// s_serve — high-concurrency static + API server for S Language (Go)
package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"time"
)

func main() {
	root := flag.String("root", ".", "static root directory")
	addr := flag.String("addr", "127.0.0.1:8080", "listen address")
	flag.Parse()

	abs, err := filepath.Abs(*root)
	if err != nil {
		log.Fatal(err)
	}
	if st, err := os.Stat(abs); err != nil || !st.IsDir() {
		log.Fatalf("root not a directory: %s", abs)
	}

	mux := http.NewServeMux()
	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]any{
			"ok": true, "engine": "S-Go", "root": abs, "time": time.Now().UTC().Format(time.RFC3339),
		})
	})
	mux.HandleFunc("/api/hello", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]string{"message": "Hello from S Go serve", "path": r.URL.Path})
	})
	mux.HandleFunc("/api/form", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "POST only", http.StatusMethodNotAllowed)
			return
		}
		if err := r.ParseForm(); err != nil {
			http.Error(w, err.Error(), 400)
			return
		}
		flat := map[string]string{}
		for k, v := range r.PostForm {
			if len(v) > 0 {
				flat[k] = v[0]
			}
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]any{"form": flat, "ok": true})
	})
	mux.HandleFunc("/api/echo", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_ = r.ParseForm()
		json.NewEncoder(w).Encode(map[string]any{"query": r.URL.Query(), "ok": true})
	})

	fs := http.FileServer(http.Dir(abs))
	mux.Handle("/", http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// prevent path escape
		if strings.Contains(r.URL.Path, "..") {
			http.Error(w, "bad path", 400)
			return
		}
		w.Header().Set("X-Powered-By", "S-Language-Go")
		fs.ServeHTTP(w, r)
	}))

	fmt.Printf("S Go serve http://%s/  root=%s\n", *addr, abs)
	log.Fatal(http.ListenAndServe(*addr, mux))
}
