# omni-polyglot

[![CI Badge](https://img.shields.io/github/actions/workflow/status/SpriteOvO/omni-polyglot/ci.yml?branch=main&style=flat-square&logo=githubactions&logoColor=white)](https://github.com/SpriteOvO/omni-polyglot/actions/workflows/ci.yml)

I believe I have, working with Claude, discovered a way to write one file that bash, zsh, fish, PowerShell, Python and a handful of other interpreters all run as their own.

> [!WARNING]
> Well, seriously. **This is a toy.** It is an experiment in abusing parsers. It has not been validated in any production environment, carries no compatibility guarantees, and should not be used as a template for real scripts.

`omni.ps1` is a single file that a dozen shells and scripting languages all accept. Each interpreter skips every section except its own, and that section prints one line:

```console
$ bash omni.ps1 alpha "beta gamma"
lang=bash version=5.3.20(1)-release argc=2 args=alpha beta gamma

$ fish omni.ps1 alpha "beta gamma"
lang=fish version=4.9.3 argc=2 args=alpha beta gamma

$ pwsh -File omni.ps1 alpha "beta gamma"
lang=powershell version=7.7.0 argc=2 args=alpha beta gamma

$ python3 omni.ps1 alpha "beta gamma"
lang=python version=3.14.10 argc=2 args=alpha beta gamma
```

## Interpreters

The last three columns list where the CI workflow runs each case.

| Interpreter | Command | Linux | macOS | Windows |
|---|---|---|---|---|
| bash | `bash omni.ps1` | yes | yes (bash 3.2) | Git Bash, MSYS2 |
| sh | `sh omni.ps1` | yes (dash) | yes (bash) | Git Bash, MSYS2 |
| shebang | `./omni.ps1` | yes | yes | - |
| dash | `dash omni.ps1` | yes | yes | MSYS2 |
| busybox ash | `busybox sh omni.ps1` | yes | - | - |
| zsh | `zsh omni.ps1` | yes | yes | MSYS2 |
| ksh93 | `ksh omni.ps1` | yes | yes | - |
| mksh | `mksh omni.ps1` | yes | - | - |
| tcsh | `tcsh omni.ps1` | yes | yes | MSYS2 |
| fish | `fish omni.ps1` | yes | yes | MSYS2 |
| PowerShell 7 | `pwsh -File omni.ps1` | yes | yes | yes |
| Windows PowerShell 5.1 | `powershell -ExecutionPolicy Bypass -File omni.ps1` | - | - | yes |
| Python 3 | `python3 omni.ps1` | yes | yes | native, MSYS2 |
| Perl 5 | `perl -x omni.ps1` | yes | yes | yes |
| Ruby | `ruby omni.ps1` | yes | yes | yes |

The sh family picks a sub-branch at run time: zsh, ksh (ksh93 and mksh), bash, or plain POSIX sh (dash, busybox ash). What `sh` and `./omni.ps1` report depends on what `/bin/sh` is on the machine.

## How it works

Interpreters fall into two groups:

- **Line-at-a-time** (the sh family, tcsh) read and run one command at a time. Only the lines before their own `exit` have to be valid for them.
- **Whole-file parsers** (PowerShell, fish, Python, Perl, Ruby) reject the file if any byte is invalid, even code they would never run. Every other section must therefore sit inside one of their comments or strings.

The routing lines at the top form a cascade. Each line switches one language into a "hidden" state (inside a comment, a string, or a jump), and later lines no longer need to be valid for that language. Only the first routing line has to be valid everywhere.

| Routing line | Python | PowerShell | fish | sh family and tcsh |
|---|---|---|---|---|
| `"""true" ,"" -eq 1` | `"""` opens a triple-quoted string that runs until `#"""` | `""` inside a string is an escaped quote, so this is the string `"true`; `,""` builds an array; `-eq` on an array filters it, the result is empty and nothing is printed | `""` followed by `"true"` is the command `true` | same as fish |
| `echo --% >/dev/null;true ' \| Out-Null <#'` | inside the string | `--%` turns everything up to `\|` into literal text, which goes to `Out-Null`; then `<#` opens a block comment | `echo` into /dev/null, then `true` with a one-line quoted argument | same as fish |
| `true '\'` | inside the string | inside the comment | `\'` is an escape inside single quotes, so the string stays open across lines | `\` is literal inside single quotes, so the string closes |
| `(exit $?0) \|\| goto CSH` | inside the string | inside the comment | inside the string | sh expands `$?0` to `$?` followed by `0`, i.e. `00`: success, `goto` is skipped. tcsh expands `$?0` to `1` (the input file name is known): failure, it jumps to `CSH:` |

After the routing lines, each section reopens the hiding construct of every other whole-file parser that has to skip it, and closes its own:

| Language | Hides other sections with | Opener | Closer |
|---|---|---|---|
| PowerShell | block comment | `<#` | `#>` |
| fish | multi-line single-quoted string | `true '\'`, `true '` | `#'` |
| Python | triple-quoted string | `"""` | `#"""` |
| tcsh | `goto` | `goto CSH` | label `CSH:` |
| Ruby | when the `#!` line does not mention ruby, Ruby skips ahead to the first `#!` line that does | `#!ruby` | `__END__` |
| Perl | `-x` skips ahead to the first `#!` line that mentions perl | `#!perl` | `__END__` |

Closers start with `#`, so a language that is executing code at that point sees them as ordinary comments.

### Characters each section must avoid

A section must not contain the closer of any language that is hiding it:

| Section | Must not contain |
|---|---|
| sh family, tcsh | `'`, `"""`, `#>`, `\` |
| PowerShell | `'`, `"""`, `\` |
| fish | `"""`, `#>`, `\` |
| Perl, Ruby | `'`, `"""`, `#>`; `\` only as an escape Python accepts, such as `\n` |
| Python | `'`, `#>` |

- `'` ends fish's hiding string, after which fish parses the rest as fish code.
- `#>` ends PowerShell's block comment.
- `"""` ends Python's hiding string.
- A backslash that is not a valid Python escape makes Python 3.12+ print a `SyntaxWarning`. The script still runs, but the tests treat any stderr output as a failure.

## Limitations

- **LF line endings and no BOM.** CRLF breaks every sh-family shell, and a BOM breaks the shebang. `.gitattributes` forces LF on checkout. Keep the file ASCII-only as well, because Windows PowerShell 5.1 reads files without a BOM in the legacy ANSI code page.
- **Perl needs `-x`.** Without it, Perl sees `#!/bin/sh`, which does not mention perl, and re-runs the file with `/bin/sh`, so you get the sh branch.
- **The `.ps1` extension is required by PowerShell on Windows** for `-File`. The other interpreters ignore the extension.
- **Linters that parse the whole file as sh** (`sh -n`, `dash -n`, ShellCheck) report errors in the bash-only and non-sh sections. This is expected.
- **Not supported:** cmd.exe (Windows picks the batch interpreter by the `.bat`/`.cmd` extension, which conflicts with `.ps1`, and cmd would execute every line including `#!`); JavaScript runtimes (the first routing line is a syntax error there). Classic csh is untested; the tcsh section reads `$tcsh`, which only tcsh defines.

## Running the tests

The test runner needs only Python 3.8+:

```sh
python3 tests/run_tests.py              # every installed interpreter; missing ones are skipped
python3 tests/run_tests.py bash fish    # only these cases; a missing interpreter is a failure
```

The runner calls `omni.ps1` with the arguments `alpha` and `beta gamma`. Each case must exit with status 0, write nothing to stderr, and print exactly one line of the form `lang=<name> version=<version> argc=2 args=alpha beta gamma`. The runner also checks that each case reached the expected branch.

## CI

`.github/workflows/ci.yml` runs the suite on `ubuntu-latest`, `macos-latest` and `windows-latest`:

- **Linux** installs busybox, fish, ksh, mksh, tcsh and zsh from apt.
- **macOS** uses the shells that ship with the system, plus fish from Homebrew.
- **Windows** runs three steps: native pwsh, Windows PowerShell, Python, Perl and Ruby; Git Bash; and an MSYS2 environment for bash, dash, zsh, tcsh, fish and Python.
