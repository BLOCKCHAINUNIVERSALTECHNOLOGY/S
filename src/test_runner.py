"""S Language built-in test runner — M2"""

from src.parser import parse_source
from src.interpreter import Interpreter
from src.errors import SError
import io
import sys


def run_code(source: str) -> tuple[str, str]:
    """Run source and capture stdout + any error message."""
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    err = ""
    try:
        program = parse_source(source, "<test>")
        interp = Interpreter()
        interp.run(program)
    except SError as e:
        err = str(e)
    except Exception as e:
        err = f"INTERNAL: {e}"
    out = sys.stdout.getvalue()
    sys.stdout = old_stdout
    return out.rstrip("\n"), err


def expect_output(name: str, source: str, expected: str) -> tuple[str, bool, str]:
    out, err = run_code(source)
    if err:
        return name, False, f"unexpected error: {err}"
    if out != expected:
        return name, False, f"expected {expected!r}, got {out!r}"
    return name, True, ""


def expect_error(name: str, source: str, fragment: str = "") -> tuple[str, bool, str]:
    out, err = run_code(source)
    if not err:
        return name, False, f"expected error containing {fragment!r}, but ran successfully: {out!r}"
    if fragment and fragment not in err:
        return name, False, f"error {err!r} does not contain {fragment!r}"
    return name, True, ""


def run_all():
    tests = []

    # ── Basics ──────────────────────────────────────────────
    tests.append(expect_output("hello",
        'print "Hello"',
        "Hello"))

    tests.append(expect_output("arithmetic",
        'print 2 + 3 * 4',
        "14"))

    tests.append(expect_output("parens",
        'print((2 + 3) * 4)',
        "20"))

    tests.append(expect_output("string concat",
        'print "Hello, " + "World!"',
        "Hello, World!"))

    tests.append(expect_output("bool true",
        'print true',
        "true"))

    tests.append(expect_output("bool false",
        'print false',
        "false"))

    tests.append(expect_output("nil",
        'print nil',
        "nil"))

    # ── Variables ───────────────────────────────────────────
    tests.append(expect_output("let",
        'let x = 42\nprint x',
        "42"))

    tests.append(expect_output("var assign",
        'var x = 1\nx = 2\nprint x',
        "2"))

    tests.append(expect_error("let reassign",
        'let x = 1\nx = 2',
        "immutable"))

    tests.append(expect_error("undefined var",
        'print missing',
        "Unknown name"))

    # ── Comparisons & logic ─────────────────────────────────
    tests.append(expect_output("comparison",
        'print 1 < 2\nprint 5 == 5\nprint 3 != 4',
        "true\ntrue\ntrue"))

    tests.append(expect_output("and short-circuit",
        'print false and (1 / 0)\nprint true and true',
        "false\ntrue"))

    tests.append(expect_output("or short-circuit",
        'print true or (1 / 0)\nprint false or false',
        "true\nfalse"))

    tests.append(expect_output("not",
        'print not true\nprint not false',
        "false\ntrue"))

    # ── If ──────────────────────────────────────────────────
    tests.append(expect_output("if true",
        'if true { print "yes" } else { print "no" }',
        "yes"))

    tests.append(expect_output("if false",
        'if false { print "yes" } else { print "no" }',
        "no"))

    # ── Loop ────────────────────────────────────────────────
    tests.append(expect_output("loop break",
        '''
        var i = 0
        loop {
            i = i + 1
            if i >= 3 { break }
        }
        print i
        ''',
        "3"))

    # ── Functions ───────────────────────────────────────────
    tests.append(expect_output("fn call",
        '''
        fn double(n: int): int {
            ret n * 2
        }
        print double(21)
        ''',
        "42"))

    tests.append(expect_output("fn string",
        '''
        fn greet(name: str): str {
            ret "Hi " + name
        }
        print greet("Queen")
        ''',
        "Hi Queen"))

    tests.append(expect_error("div by zero",
        'print 1 / 0',
        "Division by zero"))

    tests.append(expect_error("parse error",
        'let = 5',
        "Expected"))


    # ── M3: Ranges, recursion, break context ────────────────
    tests.append(expect_output("for range",
        """
        var sum = 0
        for i in 1..5 {
            sum = sum + i
        }
        print sum
        """,
        "10"))

    tests.append(expect_output("for range empty",
        """
        var count = 0
        for i in 5..5 {
            count = count + 1
        }
        print count
        """,
        "0"))

    tests.append(expect_output("factorial",
        """
        fn fact(n: int): int {
            if n <= 1 { ret 1 }
            ret n * fact(n - 1)
        }
        print fact(6)
        """,
        "720"))

    tests.append(expect_error("break outside",
        "break",
        "break outside of loop"))

    tests.append(expect_error("next outside",
        "next",
        "next outside of loop"))

    tests.append(expect_error("recursion limit",
        """
        fn boom(n: int): int {
            ret boom(n + 1)
        }
        print boom(1)
        """,
        "Maximum recursion depth"))

    tests.append(expect_output("nested loop break",
        """
        var outer = 0
        loop {
            outer = outer + 1
            var inner = 0
            loop {
                inner = inner + 1
                if inner >= 2 { break }
            }
            if outer >= 3 { break }
        }
        print outer
        """,
        "3"))



    # ── M4: Lists + Maps ───────────────────────────────────
    tests.append(expect_output("list lit",
        'print [1, 2, 3]',
        "[1, 2, 3]"))

    tests.append(expect_output("list index",
        'let a = [10, 20, 30]\nprint a[1]',
        "20"))

    tests.append(expect_output("list len",
        'print len([1, 2, 3, 4])',
        "4"))

    tests.append(expect_error("list bounds",
        'print [1, 2][5]',
        "out of bounds"))

    tests.append(expect_output("map lit",
        'let m = {"a": 1, "b": 2}\nprint m["a"]',
        "1"))

    tests.append(expect_output("map len",
        'print len({"x": 10, "y": 20})',
        "2"))

    tests.append(expect_error("map missing key",
        'print {"a": 1}["z"]',
        "not found"))

    tests.append(expect_output("for over list",
        """
        var s = 0
        for n in [1, 2, 3, 4] {
            s = s + n
        }
        print s
        """,
        "10"))

    tests.append(expect_output("nested list",
        'let m = [[1, 2], [3, 4]]\nprint m[1][0]',
        "3"))

    tests.append(expect_output("string index",
        'print "hello"[1]',
        "e"))



    # ── M6: Assert + reliability ───────────────────────────
    tests.append(expect_output("assert pass",
        "assert true\nprint \"ok\"",
        "ok"))

    tests.append(expect_error("assert fail",
        "assert false",
        "Assertion failed"))

    tests.append(expect_error("assert custom msg",
        'assert 1 > 5, "math is broken"',
        "math is broken"))

    tests.append(expect_output("assert with expr",
        "let x = 10\nassert x == 10\nprint x",
        "10"))

    tests.append(expect_error("empty list index",
        "print [][0]",
        "out of bounds"))

    tests.append(expect_output("empty list len",
        "print len([])",
        "0"))

    tests.append(expect_output("empty map len",
        'print len({})',
        "0"))



    # ── M7: Classes + safe/rescue ──────────────────────────
    tests.append(expect_output("class basic",
        """
        class Box {
            fn init(v: int): int {
                this.val = v
                ret 0
            }
            fn get(): int {
                ret this.val
            }
        }
        let b = new Box(42)
        print b.get()
        """,
        "42"))

    tests.append(expect_output("safe rescue",
        """
        safe {
            print 10 / 0
        } rescue e {
            print "err"
        }
        """,
        "err"))

    tests.append(expect_output("safe no error",
        """
        safe {
            print 2 + 2
        } rescue e {
            print "should not print"
        }
        """,
        "4"))



    tests.append(expect_output("lambda map",
        'print map([1, 2], { x -> x * 10 })',
        "[10, 20]"))
    tests.append(expect_output("coalesce",
        'print none() ?? 7',
        "7"))
    tests.append(expect_output("pipe",
        """
        fn add1(x: int): int { ret x + 1 }
        print 5 |> add1
        """,
        "6"))
    tests.append(expect_output("await async",
        """
        async fn f(): int { ret 42 }
        print await f()
        """,
        "42"))


    tests.append(expect_output("index assign",
        "var a = [1, 2]\na[0] = 9\nprint a[0]",
        "9"))
    tests.append(expect_output("in list",
        "print 2 in [1, 2, 3]",
        "true"))
    tests.append(expect_output("compound add",
        "var x = 5\nx += 3\nprint x",
        "8"))
    tests.append(expect_output("type int",
        "print type(1)",
        "int"))
    tests.append(expect_error("freeze mut",
        "let f = freeze([1])\nf[0] = 2",
        "frozen"))


    tests.append(expect_output("slice list",
        "print [1,2,3,4][1:3]",
        "[2, 3]"))
    tests.append(expect_output("ternary",
        'print true ? "a" : "b"',
        "a"))
    tests.append(expect_output("repeat",
        "var c = 0\nrepeat 3 { c += 1 }\nprint c",
        "3"))
    tests.append(expect_output("trim",
        'print trim("  x  ")',
        "x"))


    tests.append(expect_output("guard ok",
        "fn f(x: int): int { guard x > 0\n ret x }\nprint f(2)",
        "2"))
    tests.append(expect_output("multiline str",
        'print """a\nb"""',
        "a\nb"))
    tests.append(expect_output("sort unique",
        "print sort(unique([2,1,2]))",
        "[1, 2]"))


    # ── B5 / Phase B coverage ──────────────────────────────
    tests.append(expect_output("pipe svm-style",
        """
        fn add1(x: int): int { ret x + 1 }
        print 9 |> add1
        """,
        "10"))

    tests.append(expect_output("lambda pure",
        "let f = { x -> x * 3 }\nprint f(4)",
        "12"))

    tests.append(expect_output("coalesce nil",
        "print nil ?? 5",
        "5"))

    tests.append(expect_output("guard in fn",
        """
        fn g(x: int): int {
          guard x == 1
          ret 100
        }
        print g(1)
        """,
        "100"))


    tests.append(expect_output("json stringify",
        'print json_stringify({ "x": 2 })',
        '{"x": 2}'))

    tests.append(expect_output("calc add",
        "fn add(a: int, b: int): int { ret a + b }\nprint add(2, 3)",
        "5"))
    tests.append(expect_output("todo push len",
        "var t = []\npush(t, \"a\")\npush(t, \"b\")\nprint len(t)",
        "2"))
    tests.append(expect_output("guard zero",
        "fn d(a: int, b: int): int { guard b != 0\n ret a / b }\nprint d(8, 2)",
        "4"))
    tests.append(expect_output("slice str",
        'print "hello"[1:4]',
        "ell"))
    tests.append(expect_output("repeat count",
        "var n = 0\nrepeat 4 { n += 1 }\nprint n",
        "4"))
    tests.append(expect_output("pipe double",
        "fn d(x: int): int { ret x * 2 }\nprint 6 |> d",
        "12"))
    tests.append(expect_output("when expr",
        "let r = when 2 {\n 1 -> \"a\"\n 2 -> \"b\"\n else -> \"c\"\n}\nprint r",
        "b"))

    # week1 batch toward 100
    tests.append(expect_output("str upper", 'print upper("s")', "S"))
    tests.append(expect_output("str lower", 'print lower("S")', "s"))
    tests.append(expect_output("join split", 'print join(split("a,b", ","), "-")', "a-b"))
    tests.append(expect_output("in string", 'print "el" in "hello"', "true"))
    tests.append(expect_output("ternary nest", 'print true ? (false ? 1 : 2) : 3', "2"))
    tests.append(expect_output("list slice end", "print [1,2,3,4][2:]", "[3, 4]"))
    tests.append(expect_output("coalesce chain", "print nil ?? nil ?? 7", "7"))
    tests.append(expect_output("lambda pipe", "print 4 |> { x -> x + 1 }", "5"))
    tests.append(expect_output("var compound", "var x = 2\nx *= 5\nprint x", "10"))
    tests.append(expect_output("map get", 'print { "a": 9 }["a"]', "9"))
    tests.append(expect_output("opt some", "print valueOr(some(3), 0)", "3"))
    tests.append(expect_output("opt none", "print valueOr(none(), 0)", "0"))
    tests.append(expect_output("result ok", "print unwrap(ok(11))", "11"))
    tests.append(expect_output("filter even",
        "print filter([1,2,3,4], { n -> n % 2 == 0 })",
        "[2, 4]"))
    tests.append(expect_output("sum list", "print sum([1,2,3,4])", "10"))
    tests.append(expect_output("any true", "print any([false, true])", "true"))
    tests.append(expect_output("all true", "print all([true, true])", "true"))
    tests.append(expect_output("type str", 'print type("x")', "str"))
    tests.append(expect_output("freeze len", "print len(freeze([1,2]))", "2"))
    tests.append(expect_output("assert ok", "assert true\nprint 1", "1"))
    tests.append(expect_error("assert bad", "assert false", "Assertion"))
    tests.append(expect_output("class field",
        "class A { fn init(): int { this.v = 5\n ret 0 } }\nlet o = new A()\nprint o.v",
        "5"))
    tests.append(expect_output("safe ok",
        "safe { print 1 } rescue e { print 0 }",
        "1"))

    tests.append(expect_output("hash sha",
        'print len(hash("S"))',
        "64"))
    tests.append(expect_output("clock type",
        "print type(clock())",
        "dec"))


    tests.append(expect_output("min list", "print min([3,1,2])", "1"))
    tests.append(expect_output("max args", "print max(1, 9, 3)", "9"))
    tests.append(expect_output("abs neg", "print abs(0 - 5)", "5"))
    tests.append(expect_output("pad str", 'print pad("S", 4, ".")', "S..."))


    tests.append(expect_output("require ok",
        "require(true)\nprint 1",
        "1"))
    tests.append(expect_error("require fail",
        "require(false, \"bad\")",
        "bad"))
    tests.append(expect_output("check opt clean",
        "print valueOr(some(1), 0) + 1",
        "2"))


    tests.append(expect_output("min max mix", "print min(5, max(1, 3))", "3"))
    tests.append(expect_output("hash len32", 'print len(hash("ab", "md5"))', "32"))
    tests.append(expect_output("repeat zero", "var n = 1\nrepeat 0 { n = 0 }\nprint n", "1"))


    tests.append(expect_output("v3 greeter",
        'fn hi(n: str): str { ret "Hi " + n }\nprint hi("S")',
        "Hi S"))
    tests.append(expect_output("v3 counter",
        "var n = 0\nrepeat 3 { n += 1 }\nprint n",
        "3"))


    tests.append(expect_output("keys map",
        'print keys({ "a": 1 })',
        "['a']"))
    tests.append(expect_output("floor", "print floor(3.9)", "3"))
    tests.append(expect_output("clamp", "print clamp(15, 0, 10)", "10"))
    tests.append(expect_output("list concat", "print [1] + [2]", "[1, 2]"))
    tests.append(expect_output("take", "print take([1,2,3], 2)", "[1, 2]"))
    tests.append(expect_output("elif ok",
        "if false { print 0 } elif true { print 1 } else { print 2 }",
        "1"))


    tests.append(expect_output("while count",
        "var i = 0\nwhile i < 3 { i += 1 }\nprint i",
        "3"))
    tests.append(expect_output("fn default",
        'fn g(n: str = "X"): str { ret n }\nprint g()',
        "X"))
    tests.append(expect_output("fn recurse",
        "fn f(n: int): int { if n <= 1 { ret 1 }\n ret n * f(n - 1) }\nprint f(4)",
        "24"))


    tests.append(expect_output("html escape",
        'print html_escape("<x>")',
        "&lt;x&gt;"))
    tests.append(expect_output("html tag",
        'print html_tag("p", "hi")',
        "<p>hi</p>"))


    tests.append(expect_output("path join",
        'print path_join("a", "b")',
        "a/b"))
    tests.append(expect_output("csv",
        'print csv_split("a,b,c")',
        "['a', 'b', 'c']"))
    tests.append(expect_output("regex",
        'print regex_match("(\\\\d+)", "ab12cd")',
        "['12']"))
    tests.append(expect_output("date fmt year",
        'print len(date_fmt("%Y"))',
        "4"))

    # Keep focused Phase B tests in both `s test` and `s doctor`.
    from src.test_phase_b import run_all as run_phase_b
    tests.extend(run_phase_b())

    return tests
