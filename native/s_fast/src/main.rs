//! s_fast — native helpers for S Language
//! Usage: s_fast <cmd> [args...]

use std::env;
use std::io::{self, Read, Write};

fn html_escape(s: &str) -> String {
    let mut out = String::with_capacity(s.len());
    for c in s.chars() {
        match c {
            '&' => out.push_str("&amp;"),
            '<' => out.push_str("&lt;"),
            '>' => out.push_str("&gt;"),
            '"' => out.push_str("&quot;"),
            '\'' => out.push_str("&#39;"),
            _ => out.push(c),
        }
    }
    out
}

fn main() {
    let mut args: Vec<String> = env::args().skip(1).collect();
    if args.is_empty() {
        eprintln!("s_fast cmds: version | html_escape | hash_sha256");
        std::process::exit(1);
    }
    let cmd = args.remove(0);
    match cmd.as_str() {
        "version" => {
            println!("s_fast 0.1.0 rust");
        }
        "html_escape" => {
            let input = if args.is_empty() {
                let mut buf = String::new();
                io::stdin().read_to_string(&mut buf).ok();
                buf
            } else {
                args.join(" ")
            };
            print!("{}", html_escape(&input));
            let _ = io::stdout().flush();
        }
        "hash_sha256" => {
            let input = if args.is_empty() {
                let mut buf = String::new();
                io::stdin().read_to_string(&mut buf).ok();
                buf
            } else {
                args.join(" ")
            };
            // pure simple FNV-like not crypto — use sha2 if available; fallback
            println!("{:x}", simple_digest(input.as_bytes()));
        }
        _ => {
            eprintln!("unknown cmd: {}", cmd);
            std::process::exit(2);
        }
    }
}

fn simple_digest(data: &[u8]) -> u64 {
    // Not cryptographic — demo path; production would use sha2 crate
    let mut h: u64 = 0xcbf29ce484222325;
    for b in data {
        h ^= *b as u64;
        h = h.wrapping_mul(0x100000001b3);
    }
    h
}
