import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class LintError:
    line: int
    message: str
    severity: str  # "error" | "warning"


# Environments where double \\ is expected / allowed
_TABULAR_ENVS = frozenset(
    [
        "tabular",
        "tabular*",
        "tabularx",
        "array",
        "matrix",
        "pmatrix",
        "bmatrix",
        "Bmatrix",
        "vmatrix",
        "Vmatrix",
        "smallmatrix",
        "align",
        "align*",
        "aligned",
        "alignat",
        "alignat*",
        "gather",
        "gather*",
        "gathered",
        "multline",
        "multline*",
        "split",
        "eqnarray",
        "eqnarray*",
    ]
)


def lint(content: str, tex_path: Path) -> list[LintError]:
    """Fast local static analysis — no external deps, pure Python regex."""
    errors: list[LintError] = []
    lines = content.splitlines()

    # ------------------------------------------------------------------ #
    # Rule 1 & 2: environment matching + \end{document}                   #
    # ------------------------------------------------------------------ #
    begin_re = re.compile(r"\\begin\{([^}]+)\}")
    end_re = re.compile(r"\\end\{([^}]+)\}")

    # Stack of (env_name, line_number)
    env_stack: list[tuple[str, int]] = []
    # Track which envs are currently open (for Rule 5 below)
    open_envs: list[str] = []
    has_end_document = False

    for lineno, line in enumerate(lines, start=1):
        for m in begin_re.finditer(line):
            env = m.group(1)
            env_stack.append((env, lineno))
            open_envs.append(env)

        for m in end_re.finditer(line):
            env = m.group(1)
            if env == "document":
                has_end_document = True
            if env_stack and env_stack[-1][0] == env:
                env_stack.pop()
                if open_envs and open_envs[-1] == env:
                    open_envs.pop()
            elif env_stack:
                # Mismatched: try to find it deeper in the stack
                for i in range(len(env_stack) - 1, -1, -1):
                    if env_stack[i][0] == env:
                        # Everything above it is unclosed
                        unclosed = env_stack[i + 1 :]
                        for u_env, u_line in unclosed:
                            errors.append(
                                LintError(
                                    line=u_line,
                                    message=f"Unclosed environment '\\begin{{{u_env}}}' (closed outer env '{env}' first)",
                                    severity="error",
                                )
                            )
                        env_stack = env_stack[:i]
                        if open_envs and env in open_envs:
                            idx = len(open_envs) - 1 - open_envs[::-1].index(env)
                            open_envs = open_envs[:idx]
                        break
                else:
                    errors.append(
                        LintError(
                            line=lineno,
                            message=f"\\end{{{env}}} has no matching \\begin{{{env}}}",
                            severity="error",
                        )
                    )
            else:
                errors.append(
                    LintError(
                        line=lineno,
                        message=f"\\end{{{env}}} has no matching \\begin{{{env}}}",
                        severity="error",
                    )
                )

    # Any environments still on the stack are unclosed
    for env, lineno in env_stack:
        errors.append(
            LintError(
                line=lineno,
                message=f"Unclosed environment: \\begin{{{env}}} has no matching \\end{{{env}}}",
                severity="error",
            )
        )

    # Rule 2: \end{document} must be present
    if not has_end_document:
        errors.append(
            LintError(
                line=len(lines),
                message="Missing \\end{document}",
                severity="error",
            )
        )

    # ------------------------------------------------------------------ #
    # Rule 3: \input{file} where file.tex doesn't exist                   #
    # ------------------------------------------------------------------ #
    input_re = re.compile(r"\\input\{([^}]+)\}")
    base_dir = tex_path.parent

    for lineno, line in enumerate(lines, start=1):
        for m in input_re.finditer(line):
            fname = m.group(1).strip()
            # Add .tex extension if not already present
            if not fname.endswith(".tex"):
                fname_tex = fname + ".tex"
            else:
                fname_tex = fname

            candidate = base_dir / fname_tex
            if not candidate.exists():
                # Also try without adding extension in case the user used a different ext
                candidate_raw = base_dir / m.group(1).strip()
                if not candidate_raw.exists():
                    errors.append(
                        LintError(
                            line=lineno,
                            message=f"\\input{{{m.group(1)}}}: file not found ({candidate})",
                            severity="error",
                        )
                    )

    # ------------------------------------------------------------------ #
    # Rule 4: Unmatched braces (running counter)                          #
    # ------------------------------------------------------------------ #
    brace_depth = 0
    for lineno, line in enumerate(lines, start=1):
        # Skip commented-out content
        # Remove content after % (but not \%)
        stripped = re.sub(r"(?<!\\)%.*", "", line)
        for ch in stripped:
            if ch == "{":
                brace_depth += 1
            elif ch == "}":
                brace_depth -= 1
                if brace_depth < 0:
                    errors.append(
                        LintError(
                            line=lineno,
                            message="Unmatched '}': more closing braces than opening braces",
                            severity="error",
                        )
                    )
                    brace_depth = 0  # reset to continue checking

    if brace_depth > 0:
        errors.append(
            LintError(
                line=len(lines),
                message=f"Unmatched '{{': {brace_depth} unclosed brace(s) at end of file",
                severity="error",
            )
        )

    # ------------------------------------------------------------------ #
    # Rule 5: Double \\ outside tabular/array/matrix environments         #
    # ------------------------------------------------------------------ #
    double_backslash_re = re.compile(r"(?<!\\)\\\\")

    # Rebuild open-env state as we scan lines again.
    # Process order per line: opens → check \\ → closes.
    # This ensures that a \\ in "$\begin{array}{cc} a & b \\ c & d \end{array}$"
    # is correctly seen as inside the array environment.
    current_envs: list[str] = []
    for lineno, line in enumerate(lines, start=1):
        stripped = re.sub(r"(?<!\\)%.*", "", line)

        # 1) Record all \begin{} on this line (opens come first positionally)
        for m in begin_re.finditer(stripped):
            current_envs.append(m.group(1))

        # 2) Check for \\ while all opens on this line are active
        if double_backslash_re.search(stripped):
            in_tabular = any(e in _TABULAR_ENVS for e in current_envs)
            if not in_tabular:
                errors.append(
                    LintError(
                        line=lineno,
                        message="Double \\\\ outside tabular/array/matrix environment — use \\\\par or a blank line for paragraph breaks",
                        severity="warning",
                    )
                )

        # 3) Process \end{} closes after the \\ check
        for m in end_re.finditer(stripped):
            env = m.group(1)
            if env in current_envs:
                idx = len(current_envs) - 1 - current_envs[::-1].index(env)
                current_envs = current_envs[:idx] + current_envs[idx + 1 :]

    return errors
