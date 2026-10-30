"""Shared call signatures for built-in and repository-defined TeX commands."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ArgumentSpec:
    kind: str = "mandatory"
    mode: str = "math"
    default: str | None = None
    field: bool = False


@dataclass(frozen=True)
class CommandSpec:
    arguments: tuple[ArgumentSpec, ...] = ()
    context: str = "math"
    script_atom: bool = False
    paired: bool = False


def builtin_commands() -> dict[str, CommandSpec]:
    math_arguments = {
        **dict.fromkeys(
            "sqrt mathbb mathbf mathcal mathfrak mathit mathnormal mathrm mathscr "
            "mathsf mathtt boldsymbol bm overline underline widehat widetilde hat "
            "tilde bar vec dot ddot dddot ddddot breve check acute grave mathring "
            "overbrace underbrace boxed phantom hphantom vphantom mathop mathord "
            "mathbin mathrel mathopen mathclose mathpunct mathinner pmod pod ensuremath".split(),
            1,
        ),
        **dict.fromkeys(
            "frac dfrac tfrac cfrac binom dbinom tbinom overset underset stackrel".split(),
            2,
        ),
    }
    text_arguments = {
        **dict.fromkeys(
            "text textrm textsf texttt textnormal textbf textit textsl textsc textup "
            "emph mbox operatorname chapter section subsection subsubsection "
            "part paragraph subparagraph title author date caption footnote footnotetext".split(),
            1,
        ),
        "texorpdfstring": 2,
    }
    symbols = (
        "alpha beta gamma delta epsilon varepsilon zeta eta theta vartheta iota kappa "
        "varkappa lambda mu nu xi omicron pi varpi rho varrho sigma varsigma tau "
        "upsilon phi varphi chi psi omega Gamma Delta Theta Lambda Xi Pi Sigma "
        "Upsilon Phi Psi Omega infty ell hbar imath jmath partial nabla emptyset "
        "varnothing prime ast star dagger ddagger top bot perp cdot times pm mp "
        "ldots cdots vdots ddots dots sin cos tan cot sec csc log ln exp det dim "
        "gcd hom ker lim sup inf max min sum prod coprod int iint iiint oint".split()
    )
    starred = set("operatorname chapter section subsection subsubsection part paragraph subparagraph caption".split())
    optional = set(
        "sqrt cfrac chapter section subsection subsubsection part paragraph "
        "subparagraph caption footnote footnotetext".split()
    )
    commands = {name: CommandSpec(script_atom=True) for name in symbols}
    for name, count in (math_arguments | text_arguments).items():
        mode = "text" if name in text_arguments else "math"
        arguments = []
        if name in starred:
            arguments.append(ArgumentSpec("star", "opaque"))
        if name in optional:
            optional_mode = mode if name == "sqrt" or mode == "text" else "opaque"
            arguments.append(ArgumentSpec("optional", optional_mode))
        arguments.extend(ArgumentSpec(mode=mode, field=name == "sqrt") for _ in range(count))
        context = "any" if name in text_arguments or name == "ensuremath" else "math"
        commands[name] = CommandSpec(tuple(arguments), context, script_atom=True)
    return commands


BUILTIN_COMMANDS = builtin_commands()
RESERVED_COMMANDS = frozenset(BUILTIN_COMMANDS) | frozenset(
    "begin end def gdef edef xdef let futurelet newcommand renewcommand providecommand "
    "DeclareRobustCommand NewDocumentCommand RenewDocumentCommand ProvideDocumentCommand "
    "DeclareDocumentCommand DeclareMathOperator DeclarePairedDelimiter DeclarePairedDelimiterX "
    "DeclarePairedDelimiterXPP "
    "newenvironment renewenvironment RequirePackage "
    "ProvidesPackage usepackage documentclass left right middle limits nolimits "
    "input include label ref eqref pageref url path href verb directlua catcode".split()
)
