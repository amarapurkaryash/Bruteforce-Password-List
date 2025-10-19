#!/usr/bin/env python3
"""
num_wordlist_gen.py

Numbers-only wordlist generator (interactive).

Features:
- Choose charset: all digits 0-9 or a specific set (e.g., 1,3,4,5).
- Choose length mode: fixed length or range (min..max).
- Estimates number of entries and approx output file size (bytes).
- Benchmarks local write speed (small test) and estimates completion time.
- Checks free disk space and warns if insufficient; supports a 'force' proceed.
- Writes one password per line to the output file and prints each entry to terminal
  as it's produced (this can flood terminal for very large lists).
- Progress updates (entries written, elapsed time, ETA).
- Use responsibly: don't run this against systems you don't own/authorize.

"""

import os
import shutil
import time
import math
from itertools import product

def input_digits_choice():
    while True:
        choice = input("Include all digits 0-9 or specific digits? (all/specific) [all]: ").strip().lower() or "all"
        if choice in ("all","specific"):
            break
        print("Please type 'all' or 'specific'.")
    if choice == "all":
        return "0123456789"
    # specific
    while True:
        s = input("Enter digits you want to include (examples: 135 or 1,3,5): ").strip()
        s = s.replace(",", "")
        if s.isdigit() and all(ch in "0123456789" for ch in s):
            # remove duplicates while preserving order
            seen = set()
            digits = []
            for ch in s:
                if ch not in seen:
                    seen.add(ch)
                    digits.append(ch)
            return "".join(digits)
        print("Invalid input. Use digits 0-9 (e.g., 0139 or 1,3,9).")

def input_length_choice():
    while True:
        choice = input("Length mode — fixed or range? (fixed/range) [fixed]: ").strip().lower() or "fixed"
        if choice in ("fixed","range"):
            break
        print("Please type 'fixed' or 'range'.")
    if choice == "fixed":
        while True:
            try:
                L = int(input("Enter fixed length (positive integer, e.g., 5): ").strip())
                if L > 0:
                    return (L, L)
            except ValueError:
                pass
            print("Invalid length.")
    else:
        while True:
            try:
                mn = int(input("Enter min length (>=1): ").strip())
                mx = int(input("Enter max length (>=min): ").strip())
                if mn >= 1 and mx >= mn:
                    return (mn, mx)
            except ValueError:
                pass
            print("Invalid min/max lengths.")

def estimate_counts(charset_len, min_len, max_len):
    # total entries and per-length breakdown
    per_length = {}
    total = 0
    for i in range(min_len, max_len+1):
        cnt = pow(charset_len, i)
        per_length[i] = cnt
        total += cnt
    return total, per_length

def estimate_bytes(per_length):
    # each line = i chars + newline (1 byte) -> (i + 1) bytes per entry
    total_bytes = 0
    for i, cnt in per_length.items():
        total_bytes += cnt * (i + 1)
    return total_bytes

def get_free_space(path):
    try:
        st = shutil.disk_usage(path)
        # st.free is bytes available
        return st.free
    except Exception:
        return None

def benchmark_write_speed(path, trial_bytes=1_000_000):
    # writes a small temporary file to path to estimate write speed in bytes/sec
    # returns bytes_per_sec or None on failure
    tmp = os.path.join(path, ".num_wordlist_io_test.tmp")
    try:
        data = b"0" * 65536  # 64KB chunk
        written = 0
        start = time.time()
        with open(tmp, "wb") as f:
            while written < trial_bytes:
                f.write(data)
                written += len(data)
        fsize = os.path.getsize(tmp)
        elapsed = time.time() - start
        # cleanup
        try:
            os.remove(tmp)
        except Exception:
            pass
        if elapsed <= 0:
            return None
        return fsize / elapsed
    except Exception:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass
        return None

def human_readable_bytes(n):
    # simple helper
    for unit in ["B","KB","MB","GB","TB"]:
        if n < 1024:
            return f"{n:.2f} {unit}"
        n /= 1024
    return f"{n:.2f} PB"

def confirm(prompt="Proceed? (y/N): "):
    ans = input(prompt).strip().lower()
    return ans in ("y","yes")

def generate_wordlist(path, charset, min_len, max_len, print_to_terminal=True, progress_interval=10000):
    total_entries, per_length = estimate_counts(len(charset), min_len, max_len)
    total_entries_int = int(total_entries)
    written = 0
    start_time = time.time()
    with open(path, "w", encoding="utf-8") as fh:
        for length in range(min_len, max_len+1):
            # product returns tuples of characters
            for tup in product(charset, repeat=length):
                word = "".join(tup)
                fh.write(word + "\n")
                written += 1
                if print_to_terminal:
                    print(word)
                # progress and ETA every progress_interval
                if written % progress_interval == 0 or written == total_entries_int:
                    elapsed = time.time() - start_time
                    bytes_written = sum((len(w)+1) for w in [])  # placeholder, expensive to compute per-line
                    # better estimate: average length so far ~ approximated by length in loop
                    avg_len = ( (min_len + length) / 2.0 )
                    # approximate bytes written = written * (avg_len + 1)
                    approx_bytes_written = written * (avg_len + 1)
                    # use measured speed if available from outer scope? We'll compute ETA using elapsed & written
                    entries_per_sec = written / elapsed if elapsed > 0 else None
                    if entries_per_sec:
                        remaining = total_entries_int - written
                        eta_s = remaining / entries_per_sec
                        eta = time.strftime("%H:%M:%S", time.gmtime(eta_s))
                    else:
                        eta = "unknown"
                    print(f"[Progress] written {written:,}/{total_entries_int:,} entries. Elapsed: {elapsed:.1f}s. ETA: {eta}")
    total_time = time.time() - start_time
    return written, total_time

def main():
    print("=== Numbers-only wordlist generator ===")
    charset = input_digits_choice()
    print(f"Using digits: {','.join(list(charset))}")
    min_len, max_len = input_length_choice()
    out_fn = input("Output filename [wordlist.txt]: ").strip() or "wordlist.txt"
    # ensure .txt
    if not out_fn.endswith(".txt"):
        out_fn = out_fn + ".txt"
    # compute counts & sizes
    total_entries, per_length = estimate_counts(len(charset), min_len, max_len)
    total_bytes = estimate_bytes(per_length)
    print("\n--- Estimate ---")
    print(f"Charset length: {len(charset)}")
    print("Per-length counts:")
    for l, c in per_length.items():
        print(f" length {l}: {c:,} entries")
    print(f"Total entries (sum): {total_entries:,}")
    print(f"Estimated output file size (uncompressed): {human_readable_bytes(total_bytes)} ({total_bytes:,} bytes)")
    # disk space check
    path_dir = os.path.dirname(os.path.abspath(out_fn)) or "."
    free = get_free_space(path_dir)
    if free is not None:
        print(f"Free disk space at target dir: {human_readable_bytes(free)}")
        if free < total_bytes:
            print("\nWARNING: Free space is smaller than estimated output file size.")
            print("You can choose to abort or FORCE the run (you will be responsible).")
            if not confirm("Force and continue despite low disk space? (y/N): "):
                print("Aborted by user due to insufficient disk space.")
                return
    else:
        print("Could not determine free disk space on target path; proceeding with caution.")
        if not confirm("Continue? (y/N): "):
            print("Aborted by user.")
            return
    # benchmark write speed
    print("\nBenchmarking local write speed (small test) ...")
    speed = benchmark_write_speed(path_dir)
    if speed:
        print(f"Measured write speed: {human_readable_bytes(speed)}/s (approx).")
        est_time_s = total_bytes / speed if speed > 0 else None
        if est_time_s is not None:
            print(f"Estimated run time (based on write speed): {time.strftime('%H:%M:%S', time.gmtime(est_time_s))} (HH:MM:SS)")
    else:
        print("Could not measure write speed. Time estimate unavailable.")
    # final confirmation before generating
    print("\nReady to start generation.")
    print(f"Output file: {out_fn}")
    print("IMPORTANT: This will print each generated entry to the terminal as well.")
    if not confirm("Start now? (y/N): "):
        print("Aborted by user.")
        return
    # generation
    print("\n=== Starting generation ===")
    try:
        written, total_time = generate_wordlist(out_fn, charset, min_len, max_len, print_to_terminal=True, progress_interval=10000)
        print(f"\nDone. Wrote {written:,} entries to {out_fn} in {total_time:.1f} seconds.")
    except KeyboardInterrupt:
        print("\nInterrupted by user (KeyboardInterrupt). Partial file may exist.")
    except Exception as e:
        print(f"\nError during generation: {e}")

if __name__ == "__main__":
    main()
