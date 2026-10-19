/* S Mini — browser subset interpreter for S Play */
const SMini = (() => {
  function tokenize(src) {
    const tokens = [];
    let i = 0, line = 1;
    const isId = c => /[A-Za-z_]/.test(c);
    const isDigit = c => /[0-9]/.test(c);
    while (i < src.length) {
      let c = src[i];
      if (c === ' ' || c === '\t' || c === '\r') { i++; continue; }
      if (c === '\n') { tokens.push({t:'NL'}); i++; line++; continue; }
      if (c === '/' && src[i+1] === '/') { while (i < src.length && src[i] !== '\n') i++; continue; }
      if (c === '"') {
        i++; let s = '';
        while (i < src.length && src[i] !== '"') {
          if (src[i] === '\\') { i++; s += ({n:'\n',t:'\t'}[src[i]] || src[i]); i++; }
          else { s += src[i++]; }
        }
        i++; tokens.push({t:'STR', v:s}); continue;
      }
      if (isDigit(c)) {
        let n = '';
        while (isDigit(src[i])) n += src[i++];
        tokens.push({t:'NUM', v:+n}); continue;
      }
      if (isId(c)) {
        let id = '';
        while (i < src.length && (isId(src[i]) || isDigit(src[i]))) id += src[i++];
        const kw = ['let','var','fn','ret','if','else','loop','break','next','true','false','nil','and','or','not','print'];
        tokens.push(kw.includes(id) ? {t:id.toUpperCase()} : {t:'ID', v:id});
        continue;
      }
      const two = src.slice(i, i+2);
      if (['==','!=','<=','>='].includes(two)) { tokens.push({t:two}); i += 2; continue; }
      if ('+-*/%<>(){}=,'.includes(c)) { tokens.push({t:c}); i++; continue; }
      throw new Error('Unexpected ' + c + ' at line ' + line);
    }
    tokens.push({t:'EOF'});
    return tokens;
  }

  function parse(tokens) {
    let p = 0;
    const cur = () => tokens[p];
    const eat = (t) => { if (cur().t === t) { p++; return true; } return false; };
    const skipNL = () => { while (eat('NL')) {} };
    function expr() {
      let left = andExpr();
      while (eat('OR')) { const r = andExpr(); left = {k:'bin', op:'or', l:left, r}; }
      return left;
    }
    function andExpr() {
      let left = cmp();
      while (eat('AND')) { const r = cmp(); left = {k:'bin', op:'and', l:left, r}; }
      return left;
    }
    function cmp() {
      let left = term();
      while (['==','!=','<','>','<=','>='].includes(cur().t)) {
        const op = cur().t; p++; const r = term(); left = {k:'bin', op, l:left, r};
      }
      return left;
    }
    function term() {
      let left = factor();
      while (cur().t === '+' || cur().t === '-') {
        const op = cur().t; p++; const r = factor(); left = {k:'bin', op, l:left, r};
      }
      return left;
    }
    function factor() {
      let left = unary();
      while (cur().t === '*' || cur().t === '/' || cur().t === '%') {
        const op = cur().t; p++; const r = unary(); left = {k:'bin', op, l:left, r};
      }
      return left;
    }
    function unary() {
      if (eat('-') || eat('NOT')) { const op = tokens[p-1].t === 'NOT' ? 'not' : '-'; return {k:'unary', op, e:unary()}; }
      return primary();
    }
    function primary() {
      if (cur().t === 'NUM') { const v = cur().v; p++; return {k:'num', v}; }
      if (cur().t === 'STR') { const v = cur().v; p++; return {k:'str', v}; }
      if (eat('TRUE')) return {k:'bool', v:true};
      if (eat('FALSE')) return {k:'bool', v:false};
      if (eat('NIL')) return {k:'nil'};
      if (cur().t === 'ID') {
        const name = cur().v; p++;
        if (eat('(')) {
          const args = [];
          if (cur().t !== ')') { args.push(expr()); while (eat(',')) args.push(expr()); }
          if (!eat(')')) throw new Error('Expected )');
          return {k:'call', name, args};
        }
        return {k:'id', name};
      }
      if (eat('(')) { const e = expr(); if (!eat(')')) throw new Error('Expected )'); return e; }
      throw new Error('Unexpected token ' + cur().t);
    }
    function block() {
      if (!eat('{')) throw new Error('Expected {');
      skipNL();
      const stmts = [];
      while (cur().t !== '}' && cur().t !== 'EOF') { stmts.push(stmt()); skipNL(); }
      if (!eat('}')) throw new Error('Expected }');
      return stmts;
    }
    function stmt() {
      skipNL();
      if (eat('LET') || eat('VAR')) {
        const mut = tokens[p-1].t === 'VAR';
        if (cur().t !== 'ID') throw new Error('Expected name');
        const name = cur().v; p++;
        if (!eat('=')) throw new Error('Expected =');
        const value = expr();
        return {k:'let', name, value, mut};
      }
      if (eat('PRINT')) {
        const args = [expr()];
        while (eat(',')) args.push(expr());
        return {k:'print', args};
      }
      if (eat('IF')) {
        const cond = expr();
        const then = block();
        let els = null;
        skipNL();
        if (eat('ELSE')) els = cur().t === 'IF' ? [stmt()] : block();
        return {k:'if', cond, then, els};
      }
      if (eat('LOOP')) {
        const body = block();
        return {k:'loop', body};
      }
      if (eat('BREAK')) return {k:'break'};
      if (eat('NEXT')) return {k:'next'};
      if (eat('RET')) {
        let value = null;
        if (!['NL','}','EOF'].includes(cur().t)) value = expr();
        return {k:'ret', value};
      }
      if (eat('FN')) {
        if (cur().t !== 'ID') throw new Error('Expected fn name');
        const name = cur().v; p++;
        if (!eat('(')) throw new Error('Expected (');
        const params = [];
        if (cur().t !== ')') {
          params.push(cur().v); p++;
          while (eat(',')) { params.push(cur().v); p++; }
        }
        if (!eat(')')) throw new Error('Expected )');
        const body = block();
        return {k:'fn', name, params, body};
      }
      // assign or expr
      const e = expr();
      if (e.k === 'id' && eat('=')) return {k:'assign', name:e.name, value:expr()};
      return {k:'expr', e};
    }
    const stmts = [];
    skipNL();
    while (cur().t !== 'EOF') { stmts.push(stmt()); skipNL(); }
    return stmts;
  }

  function run(src) {
    const tokens = tokenize(src);
    const stmts = parse(tokens);
    const out = [];
    const env = Object.create(null);
    let breakFlag = false, nextFlag = false, retVal = undefined, returned = false;

    function evalE(e, sc) {
      if (e.k === 'num' || e.k === 'str' || e.k === 'bool') return e.v;
      if (e.k === 'nil') return null;
      if (e.k === 'id') {
        if (!(e.name in sc) && !(e.name in env)) throw new Error('Undefined ' + e.name);
        return e.name in sc ? sc[e.name] : env[e.name];
      }
      if (e.k === 'unary') {
        const v = evalE(e.e, sc);
        return e.op === 'not' ? !v : -v;
      }
      if (e.k === 'bin') {
        if (e.op === 'and') return evalE(e.l, sc) && evalE(e.r, sc);
        if (e.op === 'or') return evalE(e.l, sc) || evalE(e.r, sc);
        const a = evalE(e.l, sc), b = evalE(e.r, sc);
        switch (e.op) {
          case '+': return a + b; case '-': return a - b;
          case '*': return a * b; case '/': if (b===0) throw new Error('Division by zero'); return a / b;
          case '%': return a % b;
          case '==': return a === b; case '!=': return a !== b;
          case '<': return a < b; case '>': return a > b;
          case '<=': return a <= b; case '>=': return a >= b;
        }
      }
      if (e.k === 'call') {
        const fn = env[e.name];
        if (typeof fn !== 'function') throw new Error('Not a function: ' + e.name);
        return fn(...e.args.map(a => evalE(a, sc)));
      }
      return null;
    }

    function exec(stmts, sc) {
      for (const s of stmts) {
        if (returned || breakFlag) break;
        if (nextFlag) { nextFlag = false; continue; }
        if (s.k === 'let') {
          const v = evalE(s.value, sc);
          if (sc !== env) sc[s.name] = v; else env[s.name] = v;
        } else if (s.k === 'assign') {
          const v = evalE(s.value, sc);
          if (s.name in sc) sc[s.name] = v; else env[s.name] = v;
        } else if (s.k === 'print') {
          out.push(s.args.map(a => {
            const v = evalE(a, sc);
            if (v === null) return 'nil';
            if (v === true) return 'true';
            if (v === false) return 'false';
            return String(v);
          }).join(' '));
        } else if (s.k === 'if') {
          if (evalE(s.cond, sc)) exec(s.then, Object.create(sc));
          else if (s.els) exec(s.els, Object.create(sc));
        } else if (s.k === 'loop') {
          for (;;) {
            breakFlag = nextFlag = false;
            exec(s.body, Object.create(sc));
            if (breakFlag) { breakFlag = false; break; }
            if (returned) break;
          }
        } else if (s.k === 'break') breakFlag = true;
        else if (s.k === 'next') nextFlag = true;
        else if (s.k === 'ret') {
          retVal = s.value ? evalE(s.value, sc) : null;
          returned = true;
        } else if (s.k === 'fn') {
          env[s.name] = (...args) => {
            const local = Object.create(env);
            s.params.forEach((p, i) => local[p] = args[i]);
            const prev = returned; returned = false;
            exec(s.body, local);
            const r = returned ? retVal : null;
            returned = prev;
            return r;
          };
        } else if (s.k === 'expr') evalE(s.e, sc);
      }
    }

    exec(stmts, env);
    return out.join('\n') || '(no output)';
  }

  return { run };
})();
