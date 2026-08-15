import argparse
import json
import sys
from dataclasses import dataclass

from sympy import Abs, E, I, Float, Integer, Rational, Eq, Poly, Symbol, cos, exp, factor as sympy_factor, latex, log, pi, simplify, sin, sqrt, solve, tan
from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_application,
    implicit_multiplication,
    parse_expr,
    rationalize,
    standard_transformations,
)
from sympy.polys.polyerrors import PolynomialError


TRANSFORMATIONS = standard_transformations + (
    convert_xor,
    implicit_multiplication,
    implicit_application,
    rationalize,
)

SAFE_GLOBALS = {
    "__builtins__": {},
    "Symbol": Symbol,
    "Integer": Integer,
    "Rational": Rational,
    "Float": Float,
    "sin": sin,
    "cos": cos,
    "tan": tan,
    "sqrt": sqrt,
    "log": log,
    "exp": exp,
    "Abs": Abs,
    "pi": pi,
    "E": E,
    "I": I,
}


@dataclass
class FactorResult:
    input: str
    result: str
    reason: str


@dataclass
class SmartResult:
    input: str
    mode: str
    result: str
    reason: str


def parse_input(expr_text: str):
    text = expr_text.strip()
    if not text:
        raise ValueError("empty input")
    return parse_expr(text, transformations=TRANSFORMATIONS, global_dict=SAFE_GLOBALS, local_dict={}, evaluate=True)


def parse_equation(expr_text: str):
    text = expr_text.strip()
    if "=" not in text:
        return None
    left_text, right_text = text.split("=", 1)
    return Eq(parse_input(left_text), parse_input(right_text))


def _format_atom(expr) -> str:
    if expr.is_Integer:
        return str(int(expr))
    if expr.is_Rational:
        num = int(expr.p)
        den = int(expr.q)
        return str(num) if den == 1 else f"{num}/{den}"
    if expr.is_Symbol:
        return str(expr)
    return format_expr(expr)


def _paren_if_needed(expr) -> str:
    if expr.is_Atom or expr.is_Symbol:
        return _format_atom(expr)
    return f"({format_expr(expr)})"


def format_expr(expr) -> str:
    if expr.is_Add:
        out = []
        for i, term in enumerate(expr.as_ordered_terms()):
            if term.could_extract_minus_sign():
                piece = format_expr(-term)
                out.append(f"- {piece}" if i else f"-{piece}")
            else:
                piece = format_expr(term)
                out.append(piece if i == 0 else f"+ {piece}")
        return " ".join(out)

    if expr.is_Mul:
        coeff, rest = expr.as_coeff_Mul()
        if coeff == -1 and rest != 1:
            prefix = "-"
        elif coeff != 1:
            prefix = _format_atom(coeff)
        else:
            prefix = ""

        parts = []
        for factor in rest.as_ordered_factors():
            if factor.is_Pow:
                base, exp = factor.as_base_exp()
                parts.append(f"{_paren_if_needed(base)}^{_format_atom(exp)}")
            else:
                parts.append(_paren_if_needed(factor))

        body = "".join(parts)
        return prefix + body if prefix else body

    if expr.is_Pow:
        base, exp = expr.as_base_exp()
        return f"{_paren_if_needed(base)}^{_format_atom(exp)}"

    return _format_atom(expr)


def _poly_info(expr):
    try:
        return Poly(expr)
    except PolynomialError:
        return None


def is_polynomial_like(expr) -> bool:
    return _poly_info(expr) is not None


def reason_for(expr, factored_expr) -> str:
    if expr.is_Number:
        return "constant polynomial"

    poly = _poly_info(expr)
    if poly is None:
        return "no simple factorization found"

    if factored_expr != expr:
        return "factorization found"

    degree = poly.total_degree()
    if degree == 1:
        return "degree 1 polynomial (already irreducible)"

    if len(poly.gens) > 1:
        return f"multivariate polynomial ({len(poly.gens)} variables): no applicable factorization method"

    if degree == 2:
        try:
            disc = poly.discriminant()
            if disc.is_number and disc < 0:
                return "discriminant is negative, no real roots"
        except Exception:
            pass

    return f"degree {degree} polynomial: no simple factorization found"


def factor_result(expr_text: str) -> FactorResult:
    expr = parse_input(expr_text)
    factored = sympy_factor(expr)
    return FactorResult(expr_text.strip(), format_expr(factored), reason_for(expr, factored))


def smart_result(expr_text: str) -> SmartResult:
    raw = expr_text.strip()
    if not raw:
        raise ValueError("empty input")

    eq = parse_equation(raw)
    if eq is not None:
        symbols = sorted(eq.free_symbols, key=lambda s: s.name)
        if not symbols:
            left = simplify(eq.lhs)
            right = simplify(eq.rhs)
            return SmartResult(raw, "equation", f"{format_expr(left)} = {format_expr(right)}", "no variables to solve")

        try:
            sols = solve(eq, symbols, dict=True)
        except Exception:
            sols = []

        if not sols:
            return SmartResult(raw, "equation", "no solution", "equation has no solution")

        rendered = []
        for sol in sols:
            items = []
            for sym in symbols:
                if sym in sol:
                    items.append(f"{sym} = {format_expr(sol[sym])}")
            if items:
                rendered.append(", ".join(items))
        return SmartResult(raw, "equation", "; ".join(rendered) if rendered else "solution found", "equation solved")

    expr = parse_input(raw)
    if expr.free_symbols and is_polynomial_like(expr):
        factored = sympy_factor(expr)
        return SmartResult(raw, "factor", format_expr(factored), reason_for(expr, factored))

    if expr.free_symbols:
        simplified = simplify(expr)
        if simplified != expr:
            return SmartResult(raw, "simplify", format_expr(simplified), "simplified expression")
        return SmartResult(raw, "simplify", format_expr(simplified), "no further simplification")

    simplified = simplify(expr)
    return SmartResult(raw, "evaluate", format_expr(simplified), "numeric evaluation")


def factor_text(expr_text: str) -> str:
    r = factor_result(expr_text)
    return "\n".join((f"input> {r.input}", f"result> {r.result}", f"reason> {r.reason}"))


def factor_json(expr_text: str) -> str:
    r = factor_result(expr_text)
    return json.dumps({"input": r.input, "result": r.result, "reason": r.reason}, ensure_ascii=False)


def factor_xml(expr_text: str) -> str:
    r = factor_result(expr_text)
    return "\n".join(
        (
            '<?xml version="1.0" encoding="UTF-8"?>',
            "<factorization>",
            f"  <input>{escape_xml(r.input)}</input>",
            f"  <result>{escape_xml(r.result)}</result>",
            f"  <reason>{escape_xml(r.reason)}</reason>",
            "</factorization>",
        )
    )


def factor_latex(expr_text: str) -> str:
    r = factor_result(expr_text)
    expr = parse_input(expr_text)
    factored = sympy_factor(expr)
    return "\n".join(
        (
            r"\begin{aligned}",
            rf"\text{{input}} & = {latex(expr)} \\",
            rf"\text{{result}} & = {latex(factored)} \\",
            rf"\text{{reason}} & = \text{{{latex_text(r.reason)}}}",
            r"\end{aligned}",
        )
    )


def smart_text(expr_text: str) -> str:
    r = smart_result(expr_text)
    return "\n".join((f"input> {r.input}", f"mode> {r.mode}", f"result> {r.result}", f"reason> {r.reason}"))


def smart_json(expr_text: str) -> str:
    r = smart_result(expr_text)
    return json.dumps({"input": r.input, "mode": r.mode, "result": r.result, "reason": r.reason}, ensure_ascii=False)


def smart_xml(expr_text: str) -> str:
    r = smart_result(expr_text)
    return "\n".join(
        (
            '<?xml version="1.0" encoding="UTF-8"?>',
            "<smartcalc>",
            f"  <input>{escape_xml(r.input)}</input>",
            f"  <mode>{escape_xml(r.mode)}</mode>",
            f"  <result>{escape_xml(r.result)}</result>",
            f"  <reason>{escape_xml(r.reason)}</reason>",
            "</smartcalc>",
        )
    )


def smart_latex(expr_text: str) -> str:
    r = smart_result(expr_text)
    if "=" in expr_text:
        shown = parse_equation(expr_text)
    else:
        shown = parse_input(expr_text)
    return "\n".join(
        (
            r"\begin{aligned}",
            rf"\text{{input}} & = {latex(shown)} \\",
            rf"\text{{mode}} & = \text{{{latex_text(r.mode)}}} \\",
            rf"\text{{result}} & = \text{{{latex_text(r.result)}}} \\",
            rf"\text{{reason}} & = \text{{{latex_text(r.reason)}}}",
            r"\end{aligned}",
        )
    )


def escape_xml(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def latex_text(text: str) -> str:
    return text.replace("\\", r"\textbackslash{}").replace("_", r"\_")


def factor(expr_text: str) -> str:
    return factor_text(expr_text)


def smart(expr_text: str) -> str:
    return smart_text(expr_text)


def main() -> int:
    parser = argparse.ArgumentParser(description="Native Python smart calculator")
    parser.add_argument("expr", nargs="*", help="Expression to calculate")
    parser.add_argument("--mode", choices=["auto", "factor", "eval"], default="auto")
    parser.add_argument("--format", choices=["text", "json", "xml", "latex"], default="text")
    args = parser.parse_args()

    exports = "factor, factor_json, factor_latex, factor_text, factor_xml, smart, smart_json, smart_latex, smart_text, smart_xml"
    print(f"exports: {exports}")

    if args.mode == "factor":
        formatter = {
            "text": factor_text,
            "json": factor_json,
            "xml": factor_xml,
            "latex": factor_latex,
        }[args.format]
    else:
        formatter = {
            "text": smart_text,
            "json": smart_json,
            "xml": smart_xml,
            "latex": smart_latex,
        }[args.format]

    if args.expr:
        print(formatter(" ".join(args.expr)))
        return 0

    print("输入算式后回车，直接回车退出。")
    while True:
        try:
            line = input("> ").strip()
        except EOFError:
            break
        if not line:
            break
        try:
            print(formatter(line))
        except Exception as exc:
            print(f"错误: {exc}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
