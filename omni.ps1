#!/bin/sh
# Polyglot toy, see README.md. The next four lines route every interpreter to its own section below; do not edit them unless you have read the README.
"""true" ,"" -eq 1
echo --% >/dev/null;true ' | Out-Null <#'
true '\'
(exit $?0) || goto CSH
# ==== sh family: bash, dash, busybox ash, zsh, ksh93, mksh ====
# Forbidden here: single quote, triple double quote, hash followed by greater-than, backslash.
if [ -n "${ZSH_VERSION-}" ]; then
    echo "lang=zsh version=$ZSH_VERSION argc=$# args=$*"
    exit 0
fi
if [ -n "${KSH_VERSION-}" ]; then
    echo "lang=ksh version=$KSH_VERSION argc=$# args=$*"
    exit 0
fi
if [ -z "${BASH_VERSION-}" ]; then
    echo "lang=sh version=posix argc=$# args=$*"
    exit 0
fi
# Every other shell has exited by now, so bash-only syntax is safe below.
words=(only bash parses this)
[[ ${#words[@]} -eq 4 ]] && echo "lang=bash version=$BASH_VERSION argc=$# args=$*"
exit 0
# ==== tcsh ====
# Forbidden here: same as the sh family.
CSH:
echo "lang=tcsh version=$tcsh argc=$#argv args=$argv"
exit 0
#>
# ==== PowerShell: pwsh and Windows PowerShell 5.1 ====
# Forbidden here: single quote, triple double quote, backslash.
Write-Output "lang=powershell version=$($PSVersionTable.PSVersion) argc=$($args.Count) args=$($args -join " ")"
exit 0
<#
#'
# ==== fish ====
# Forbidden here: triple double quote, hash followed by greater-than, backslash.
echo "lang=fish version=$FISH_VERSION argc="(count $argv)" args=$argv"
exit 0
true '
# ==== Perl (run with perl -x) and Ruby ====
# Forbidden here: single quote, triple double quote, hash followed by greater-than; backslashes only as escapes that Python also accepts.
#!perl
printf "lang=perl version=%vd argc=%d args=%s\n", $^V, scalar @ARGV, "@ARGV";
exit 0;
__END__
#!ruby
puts "lang=ruby version=#{RUBY_VERSION} argc=#{ARGV.size} args=#{ARGV.join(" ")}"
exit 0
__END__
#"""
# ==== Python ====
# Forbidden here: single quote, hash followed by greater-than.
import platform
import sys

print("lang=python version=%s argc=%d args=%s" % (platform.python_version(), len(sys.argv) - 1, " ".join(sys.argv[1:])))
sys.exit(0)
#'
#>
