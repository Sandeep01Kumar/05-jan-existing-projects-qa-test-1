# Crashlytics NDK Architecture Analysis — `hao-backprop-test` Repository

## 1. Executive Summary

The repository under analysis is `hao-backprop-test` `[README.md:L1]` — a minimal Node.js HTTP test fixture authored as a Backprop integration target `[README.md:L2]` — and it does not contain any Firebase Crashlytics, Android NDK, JNI, or minidump code. The repository's sole runnable source is `[server.js]` (14 lines, 342 bytes), which uses only the Node.js built-in `http` module `[server.js:L1]` to start an HTTP server bound to `127.0.0.1:3000` `[server.js:L3-L4]` that responds with `Hello, World!\n` `[server.js:L9]`; `[package.json]` declares zero `dependencies` and zero `devDependencies` (npm name `hello_world`, version `1.0.0`, MIT license); and `[package-lock.json]` (lockfileVersion `3`) carries no transitive package tree at all — its `packages` object contains only the root project entry. A recursive, case-insensitive, text-only `grep -rIi -E` for the regex `crashlytics|firebase|ndk|signal_handler|sigaction|minidump|breakpad|crashpad|JNIEXPORT|JNICALL|jni\.h|backoff|retry|upload` over the repository's pre-analysis source-text files — `*.js`, `*.json`, `*.md`, `*.java`, `*.txt`, `*.csv` — explicitly excluding `.git/`, `blitzy/`, and the new `docs/` directory which IS this analysis, returns zero matches (exit status 1); a `find` for native and Android build-system file patterns (`*.c`, `*.cpp`, `*.cc`, `*.h`, `*.hpp`, `*.kt`, `*.kts`, `*.gradle`, `Android.mk`, `CMakeLists.txt`, `AndroidManifest.xml`, `*.aar`, `*.apk`) similarly returns zero files. This empirical absence is independently corroborated by the controlling Technical Specification: `[Tech Spec §3.1]` documents JavaScript (Node.js) as the primary language and Java as a non-functional stub language; `[Tech Spec §3.3]` documents zero open-source dependencies; and the preservation directive at `[README.md:L1-L2]` — formalized as `[Tech Spec §5.5.2: C-001]` "Repository must remain unchanged" — prohibits the introduction of Crashlytics code into this fixture even if such an introduction were otherwise desired. This report therefore documents the empirical absence of the requested subject matter and provides a reference description of the canonical Crashlytics NDK architecture for the reader's conceptual frame.

## 2. Repository Identification

The repository under analysis is identified by the authoritative artifacts in the table below. Every row cites the empirical source file or the controlling Technical Specification section that grounds the claim.

| Field | Value | Source |
|-------|-------|--------|
| Project name (root README header) | `hao-backprop-test` | `[README.md:L1]` |
| Preservation directive | `test project for backprop integration. Do not touch!` | `[README.md:L2]` |
| npm package `name` | `hello_world` | `[package.json:L2]` |
| Version | `1.0.0` | `[package.json:L3]` |
| Description | `Hello world in Node.js` | `[package.json:L4]` |
| `main` entry (declared) | `index.js` — note: no `index.js` file exists in the repository; the runnable file is `server.js` | `[package.json:L5]`, `[server.js]` |
| Author | `hxu` | `[package.json:L9]` |
| License | `MIT` | `[package.json:L10]`, `[Tech Spec §5.5.2: C-004]` |
| `scripts.test` | `echo "Error: no test specified" && exit 1` (npm default placeholder) | `[package.json:L7]` |
| Declared `dependencies` | (field absent) | `[package.json]` |
| Declared `devDependencies` | (field absent) | `[package.json]` |
| Lockfile version | `3` | `[package-lock.json]` |
| Lockfile installed packages | only the root project entry; no transitive tree | `[package-lock.json]` |
| Sole runnable source | `[server.js]` — 14-line Node.js HTTP server using only the built-in `http` module `[server.js:L1]`, binding `127.0.0.1:3000` `[server.js:L3-L4]`, returning `Hello, World!\n` `[server.js:L9]` | `[server.js]` |
| Primary language | JavaScript (Node.js) | `[server.js]`, `[Tech Spec §3.1]` |
| Secondary language (non-functional stubs) | Java | `[LoginTest.java]`, `[Tech Spec §3.1]` |
| Total files at repository root | 18, no subdirectories | repository inventory |
| External dependencies | 0 declared, 0 installed | `[package.json]`, `[package-lock.json]`, `[Tech Spec §3.3]` |
| System overview (Tech Spec) | Node.js HTTP fixture, localhost-only, zero dependencies | `[Tech Spec §1.1]`, `[Tech Spec §1.2]` |

The 18 root-level files are: `README.md`, `package.json`, `package-lock.json`, `server.js`, `server - Copy.js`, `LoginTest.java`, `LoginTest - Copy.java`, `industry.csv`, `industry - Copy.csv`, `test.py.txt`, `test.py - Copy.txt`, `test.txt.txt`, `100Pages.pdf`, `100Pages - Copy.pdf`, `demo.jpg`, `demo - Copy.jpg`, `sample.doc`, and `sample - Copy.doc`. The presence of the `- Copy` duplicate variants is intentional — the repository is a duplicate-detection fixture for the Backprop tool — and bit-identical duplication is verified for the relevant pairs by `diff -q` returning exit code 0 (i.e., `[server.js]` ↔ `[server - Copy.js]` and `[LoginTest.java]` ↔ `[LoginTest - Copy.java]`). The runtime surface of the repository, in full, is the 14-line `[server.js]` file reproduced below for context. It is included here because it is the **only** runnable source file in the project and it implements no networking pattern related to crash reporting (no JNI, no native invocation, no signal handling, no HTTPS outbound, no minidump processing):

```javascript
const http = require('http');

const hostname = '127.0.0.1';
const port = 3000;

const server = http.createServer((req, res) => {
  res.statusCode = 200;
  res.setHeader('Content-Type', 'text/plain');
  res.end('Hello, World!\n');
});

server.listen(port, hostname, () => {
  console.log(`Server running at http://${hostname}:${port}/`);
});
```

This is the entire JavaScript surface of the repository; no other `.js` file is present except `[server - Copy.js]`, which is bit-identical to `[server.js]` (verified via `diff -q server.js 'server - Copy.js'`, which returns silently with exit code 0). The two `.java` files (`[LoginTest.java]` and its bit-identical `[LoginTest - Copy.java]`) are 12-line, 128-byte invalid Java stubs that will not compile — `[LoginTest.java:L1]` declares `package com.blitzyTest;`, `[LoginTest.java:L3]` declares `public class LoginTest`, `[LoginTest.java:L5]` declares the conventional `public static void main(String[] args)` signature, and `[LoginTest.java:L7]` — inside that method's body — contains only the bare token `Web` with no preceding type, no following parentheses, and no terminating semicolon. The token `Web` is not a declared identifier, not an imported symbol, and not a valid Java statement; `javac` rejects the file. The remaining root files are 0-byte text placeholders (`[test.txt.txt]`, `[test.py.txt]`, `[test.py - Copy.txt]`), a 43-row CSV pair (`[industry.csv]` and `[industry - Copy.csv]`), and three pairs of binary fixture assets (`[100Pages.pdf]` / `[100Pages - Copy.pdf]` at 9,456,545 bytes each; `[demo.jpg]` / `[demo - Copy.jpg]` at 2,123,398 bytes each; `[sample.doc]` / `[sample - Copy.doc]` at 98,304 bytes each), none of which contains source code or build configuration of any kind.

## 3. Search Methodology and Evidence

This section documents the empirical searches performed to locate any Crashlytics NDK architecture component in this repository. The two principal searches are (a) a recursive grep for Crashlytics-domain terms over source-text files and (b) a `find` for the file-extension patterns that conventionally hold native and Android source. Both searches return zero project-source matches.

### 3.1 Term-Search (recursive, case-insensitive, text-only)

The following regex captures the canonical Firebase Crashlytics NDK token set — product names, native crash-handling primitives, JNI vocabulary, minidump/Breakpad/Crashpad components, and upload/retry vocabulary — as a single alternation:

```text
crashlytics|firebase|ndk|signal_handler|sigaction|minidump|breakpad|crashpad|JNIEXPORT|JNICALL|jni\.h|backoff|retry|upload
```

The grep was executed recursively (`-r`) with `-I` (text-only — binary files are skipped), `-i` (case-insensitive), and `-E` (extended regex), explicitly excluding the `.git/` directory, the `blitzy/` working directory, and the new `docs/` directory which **is** this analysis (the new `docs/analysis/` files necessarily mention every term in the regex, so including them would create a self-citation cycle and would not test the pre-analysis state of the repository):

```text
grep -rIi -E --exclude-dir=.git --exclude-dir=blitzy --exclude-dir=docs \
     'crashlytics|firebase|ndk|signal_handler|sigaction|minidump|breakpad|crashpad|JNIEXPORT|JNICALL|jni\.h|backoff|retry|upload' .
```

**Result: exit code 1 — zero matches in any project source-text file.**

The only matches anywhere in the unfiltered tree were excluded by design and are non-substantive:

1. `.git/hooks/fsmonitor-watchman.sample` — a Git-supplied sample template (not a project file) containing the unrelated Perl identifier `$retry` inside a filesystem-monitoring snippet. This file is shipped by Git itself and exists in every `git init`'d repository on this version of Git; it is not authored by this repository and carries no Crashlytics significance.
2. Coincidental byte-pattern matches inside `[100Pages.pdf]` and `[100Pages - Copy.pdf]` if `-I` is omitted. PDF is a binary container format; without the text-only filter `grep` would report any matching byte sequence inside the binary stream. These are not source-code Crashlytics references; the `-I` flag in the search above correctly skips them.

Neither of these accidental hits is a Crashlytics-domain source-code occurrence. The empirical conclusion is that the repository's project source contains zero references to any term in the regex.

### 3.2 Native and Android File-Glob Search

The second search enumerates the file-extension patterns that conventionally hold native (C/C++), JVM (Kotlin), and Android build/manifest content:

```text
*.c   *.cpp   *.cc   *.h   *.hpp
*.kt  *.kts   *.gradle
Android.mk   CMakeLists.txt   AndroidManifest.xml
*.aar   *.apk
```

The equivalent `find` invocation, again excluding `.git/`, `blitzy/`, and `docs/`:

```text
find . -path ./.git -prune -o -path ./blitzy -prune -o -path ./docs -prune -o \
       \( -name '*.c' -o -name '*.cpp' -o -name '*.cc' -o -name '*.h' -o -name '*.hpp' \
        -o -name '*.kt' -o -name '*.kts' -o -name '*.gradle' \
        -o -name 'Android.mk' -o -name 'CMakeLists.txt' -o -name 'AndroidManifest.xml' \
        -o -name '*.aar' -o -name '*.apk' \) -print
```

**Result: zero files.** The repository contains no C source, no C++ source, no header files, no Kotlin source, no Gradle build script (root or module), no Android manifest, no native build descriptor (CMake or Android.mk), and no Android binary artifact (AAR or APK).

### 3.3 Tech-Spec Corroboration

The controlling Technical Specification corroborates the empirical findings of §3.1 and §3.2:

- `[Tech Spec §1.1]` and `[Tech Spec §1.2]` characterize the repository as a Node.js HTTP fixture bound to localhost with zero dependencies.
- `[Tech Spec §3.1]` enumerates the languages in the repository: JavaScript (Node.js) as the primary language, and Java as a secondary, non-functional stub language. No Kotlin, no C, no C++.
- `[Tech Spec §3.2]` enumerates the frameworks and libraries: only the Node.js built-in `http` module. No Firebase SDK, no Crashlytics, no JNI runtime, no Breakpad, no Crashpad.
- `[Tech Spec §3.3]` enumerates open-source dependencies: none.

The empirical state and the Technical Specification therefore agree completely: there is no Crashlytics, no NDK, no JNI, no native code, no Android build system, and no minidump infrastructure in this repository.

## 4. Reference Architecture (industry-standard, for comparison only)

This section describes what a canonical Firebase Crashlytics Android NDK crash-handling architecture looks like at a conceptual level, **so that the reader has a frame of reference against which the empirical absence in this repository can be measured**. Each subsection is a conceptual description and is flagged accordingly. Nothing in this section is a claim about code present in this repository.

### 4.1 Signal Handlers

A canonical Crashlytics NDK crash handler installs a POSIX `sigaction(2)` handler for the fatal-signal set: `SIGSEGV` (segmentation fault — typically a null-pointer or out-of-bounds memory access), `SIGBUS` (bus error — typically a misaligned access or a memory-mapped I/O failure), `SIGABRT` (abort — raised by `abort(3)` and by failed `assert(3)` calls), `SIGILL` (illegal instruction — typically a corrupted instruction stream or unsupported CPU instruction), `SIGFPE` (floating-point exception — division by zero, integer overflow on certain architectures), and `SIGTRAP` (trap — used by some breakpoint/checker tooling). The handler is registered with the `SA_SIGINFO` flag so that it receives the full three-argument siginfo signature `void handler(int signo, siginfo_t *info, void *context)`, where `info->si_addr` carries the faulting address (for `SIGSEGV`/`SIGBUS`) and `context` is a pointer to a `ucontext_t` carrying the CPU register state at the moment of the fault — general-purpose registers, instruction pointer, stack pointer, and link register on architectures that have one. A dedicated alternate signal stack is installed via `sigaltstack(2)` with the `SA_ONSTACK` flag so that a stack-overflow crash (whose own stack is exhausted) can still be handled — without `sigaltstack`, the kernel would deliver the fatal signal on the already-exhausted stack and the process would terminate before the handler runs. Inside the handler the implementation is bound by the POSIX async-signal-safety contract `[signal-safety(7)]`: only functions on the async-signal-safe list (e.g., `write(2)`, `_exit(2)`, `read(2)`, `open(2)`, `close(2)`, `fsync(2)`, `rename(2)`, `clock_gettime(2)`) may be called; `malloc(3)`/`free(3)`, `printf(3)` family, `pthread_mutex_lock(3)`, and most C++ runtime facilities are NOT async-signal-safe and would cause undefined behavior (typically deadlock or memory corruption) if called from the handler. `[inferred — industry-standard description, no direct repository source]`

A conceptual signature illustrating the registration pattern follows. This code is illustrative only and is NOT present anywhere in this repository:

```c
// [inferred — industry-standard description, no direct repository source]
#include <signal.h>
#include <stdint.h>

static void fatal_signal_handler(int signo, siginfo_t *info, void *context) {
    /* Capture register state from `context` (a ucontext_t*),
     * walk and copy the stack into a pre-allocated buffer,
     * write the minidump to disk using only async-signal-safe primitives
     * (open, write, fsync, rename), then chain to the previously
     * installed handler or call _exit(128 + signo). */
}

static uint8_t alt_stack_buf[SIGSTKSZ];

static int install_crash_handler(void) {
    stack_t ss = { .ss_sp = alt_stack_buf, .ss_size = sizeof(alt_stack_buf), .ss_flags = 0 };
    if (sigaltstack(&ss, NULL) != 0) return -1;

    struct sigaction sa = {0};
    sa.sa_sigaction = fatal_signal_handler;
    sa.sa_flags     = SA_SIGINFO | SA_ONSTACK;
    sigemptyset(&sa.sa_mask);

    int signals[] = { SIGSEGV, SIGBUS, SIGABRT, SIGILL, SIGFPE, SIGTRAP };
    for (size_t i = 0; i < sizeof(signals)/sizeof(signals[0]); ++i) {
        if (sigaction(signals[i], &sa, NULL) != 0) return -1;
    }
    return 0;
}
```

The handler must also account for re-entrant fatal signals (a crash inside the handler itself) — canonical implementations either (a) restore the previous handler and `raise(signo)` to re-trigger the original behavior, or (b) call `_exit(2)` directly once the minidump has been flushed, bypassing the C++ atexit chain to avoid running destructors on potentially-corrupted state. `[inferred — industry-standard description, no direct repository source]`

### 4.2 JNI Bridge

A canonical Crashlytics NDK exposes a native library — typically `libcrashlytics.so` or a similarly-named shared object — that is loaded into the application process by a Java/Kotlin `System.loadLibrary("crashlytics")` call at SDK initialization time. The Android runtime invokes the library's `JNI_OnLoad(JavaVM *vm, void *reserved)` entry point immediately after loading, and the implementation uses this opportunity to (a) negotiate the JNI version with the VM via `(*vm)->GetEnv(vm, ..., JNI_VERSION_1_6)`, (b) look up the Java class that will own the native methods via `(*env)->FindClass(env, "com/google/firebase/crashlytics/ndk/JniNativeApi")` (or its analog), and (c) bind native function pointers to the class's Java-declared `native` methods via `(*env)->RegisterNatives(env, cls, methods, n)`. The `RegisterNatives` path is preferred over the older name-mangling convention because it (a) avoids leaking C function names through the SDK's exported symbol table, (b) allows obfuscated/short native names which improves binary size, and (c) makes the bridge resilient to Java-side package renames that would otherwise break name mangling. `[inferred — industry-standard description, no direct repository source]`

The JNI bridge is the **seam** between the async-signal-safe native crash-capture path and the higher-level Java/Kotlin crash-reporting framework. When a crash occurs and the native handler finishes writing the minidump to app-private storage, control returns to the (now-defunct) process either through `_exit` or through re-raising the fatal signal. The Java upload path runs on the **next** application launch: on `Application.onCreate()`, the Crashlytics SDK enumerates the persisted minidump directory (see §4.3) and queues each pending report for upload through the SDK's normal upload pipeline. The JNI bridge is also exercised in the non-crash direction — Java passes configuration (crash directory path, user identifier, custom keys, breadcrumbs) **down** to the native layer at SDK initialization so that the native handler has everything it needs to write a complete minidump without making any further JNI calls from the signal handler (because JNI calls are not async-signal-safe). `[inferred — industry-standard description, no direct repository source]`

A conceptual `JNI_OnLoad` and `RegisterNatives` pattern follows. This code is illustrative only and is NOT present anywhere in this repository:

```c
// [inferred — industry-standard description, no direct repository source]
#include <jni.h>

static jint native_init(JNIEnv *env, jclass clazz, jstring crash_dir) {
    const char *dir = (*env)->GetStringUTFChars(env, crash_dir, NULL);
    /* Persist `dir` for later use by the (async-signal-safe) signal handler;
     * install the signal handlers (see §4.1); register sigaltstack;
     * cache the JavaVM* for later up-call after crash drain on next launch. */
    (*env)->ReleaseStringUTFChars(env, crash_dir, dir);
    return /* success indicator */ 0;
}

static const JNINativeMethod methods[] = {
    { "nativeInit", "(Ljava/lang/String;)I", (void *)native_init },
    /* additional bindings: nativeSetUserId, nativeAddBreadcrumb,
     * nativeSetCustomKey, nativeWriteMinidumpForTest, ... */
};

JNIEXPORT jint JNICALL JNI_OnLoad(JavaVM *vm, void *reserved) {
    JNIEnv *env = NULL;
    if ((*vm)->GetEnv(vm, (void **)&env, JNI_VERSION_1_6) != JNI_OK) {
        return -1;
    }
    jclass cls = (*env)->FindClass(env, "com/google/firebase/crashlytics/ndk/JniNativeApi");
    if (cls == NULL) return -1;

    if ((*env)->RegisterNatives(env, cls, methods,
                                sizeof(methods) / sizeof(methods[0])) != 0) {
        return -1;
    }
    return JNI_VERSION_1_6;
}
```

Note that `JNI_OnLoad` itself runs on the (Java-) calling thread at `System.loadLibrary` time, NOT inside the signal handler, so it is free to use any JNI/JVM facility. Once the native crash handler runs (later, inside a fatal signal), the JNI environment pointer that was cached at `JNI_OnLoad` time is intentionally **not** dereferenced — because doing so could re-enter the JVM in a state where the JVM's own locks are held by the now-corrupted faulting thread. The signal handler instead writes the minidump to disk using only async-signal-safe primitives; the Java side picks it up on next launch via the persistent queue (§4.3). `[inferred — industry-standard description, no direct repository source]`

### 4.3 Minidump Generation

A canonical Crashlytics NDK minidump generator captures, at the moment a fatal signal is delivered, a **structured snapshot** sufficient for offline post-mortem analysis. The snapshot is written using only async-signal-safe primitives and is bounded in size so that a crashing process — which may already have corrupted heap state — can flush it to disk before the operating system terminates the process. The captured data includes: (a) **CPU register state** for the faulting thread — general-purpose registers, instruction pointer, stack pointer, link register (where applicable), and architecture-specific registers (e.g., FPU/NEON state on ARM, XMM/YMM on x86_64) — sourced from the `ucontext_t *` delivered as the third argument to the `SA_SIGINFO` handler; (b) **stack memory** — typically the top N kilobytes of the faulting thread's stack, copied verbatim so that the post-mortem symbolicator can reconstruct local variables and the call chain; (c) **per-thread state** — for every other thread in the process, a similar register snapshot and a smaller stack window (obtained by suspending sibling threads via the kernel's `tgkill(2)` / `ptrace(2)` mechanisms, or by reading `/proc/self/task/<tid>/stat` and `/proc/self/task/<tid>/syscall`); (d) **loaded module list** — for each shared object loaded into the process, the file path, the base load address, the size of the mapped region, and a build identifier (the GNU build-ID note section, conventionally `NT_GNU_BUILD_ID`) for offline symbolication; (e) **signal/exception metadata** — `signo`, `info->si_code`, `info->si_addr` (the faulting address for `SIGSEGV`/`SIGBUS`), and the timestamp of the fault. `[inferred — industry-standard description, no direct repository source]`

The output format is the **Microsoft Minidump file format** (`MDMP`) — a binary container originally specified by Microsoft for Windows post-mortem debugging and adopted as the de-facto cross-platform crash-report format by Breakpad and Crashpad. An `MDMP` file consists of a header followed by a directory of typed **streams**; the streams a Crashlytics NDK minidump typically carries are `MINIDUMP_THREAD_LIST` (per-thread register + stack tuple), `MINIDUMP_MODULE_LIST` (one entry per loaded shared object with path, load address, size, and build-ID), `MINIDUMP_EXCEPTION_STREAM` (the captured signal/exception metadata), `MINIDUMP_SYSTEM_INFO` (CPU architecture, OS version, processor count), `MINIDUMP_MEMORY_LIST` (the captured stack memory windows), and `MINIDUMP_MISC_INFO_STREAM` (process times, build identifier). The on-disk layout is compact, self-describing, and parseable by any minidump-aware debugger or symbolicator (Breakpad's `minidump_stackwalk`, Google's Crashpad tooling, Microsoft Visual Studio's WinDbg, LLDB with the appropriate plugin). `[inferred — industry-standard description, no direct repository source]`

Write semantics are governed by the async-signal-safety constraint: the file is opened via `open(2)` to a fixed path under the app-private crash directory (received via the JNI bridge at initialization time and cached in a static `char` buffer), written with one or more `write(2)` calls in a streaming fashion (no `printf` or `snprintf`, which are not async-signal-safe — formatting must be done with hand-written numeric-to-string conversions), `fsync(2)`'d to force the bytes to physical storage, `close(2)`'d, and then atomically `rename(2)`'d from a temporary `.dmp.partial` name into its final `.dmp` form. The atomic rename ensures that the Java upload path on the next launch never sees a partially-written minidump — it sees either a fully-written one or no file at all. No `malloc` is performed inside the handler; all buffers (the alternate signal stack, the minidump-builder scratch buffer, the per-thread snapshot buffer) are pre-allocated at SDK initialization time before the first crash can occur. `[inferred — industry-standard description, no direct repository source]`

## 5. Findings — Component-by-Component Absence Table

The empirical findings of §3, organized by canonical Crashlytics NDK architecture component, are summarized in the table below. Every row reports the component, the finding, and the evidence that grounds the finding.

| Expected Component | Finding | Evidence |
|--------------------|---------|----------|
| Signal handlers (`sigaction` for `SIGSEGV`/`SIGBUS`/`SIGABRT`/`SIGILL`/`SIGFPE`/`SIGTRAP`) | Not present | Zero matches in source grep for `sigaction`, `signal_handler` (§3.1); `[server.js]` is the only runnable source and uses no signal APIs — it imports only the Node.js built-in `http` module `[server.js:L1]` and `Process.on('SIGTERM')`-style signal handling does not appear anywhere in the repository |
| JNI bridge (`JNI_OnLoad` / `RegisterNatives` / `JNIEXPORT` / `JNICALL`) | Not present | Zero matches in source grep for `JNIEXPORT`, `JNICALL`, `jni\.h` (§3.1); no `.cpp`/`.c`/`.h`/`.hpp` files exist anywhere in the repository (§3.2); the two Java files (`[LoginTest.java]` and bit-identical `[LoginTest - Copy.java]`) contain no JNI symbols, declare no `native` methods, and do not even compile because `[LoginTest.java:L7]` contains only the bare token `Web` |
| Minidump generation (Breakpad / Crashpad style `MDMP` writer) | Not present | Zero matches in source grep for `minidump`, `breakpad`, `crashpad` (§3.1); no native source files in which such a writer could live (§3.2); no dependency that would supply a prebuilt minidump library — `[package.json]` declares zero `dependencies` and zero `devDependencies`, `[package-lock.json]` (lockfileVersion 3) carries no transitive tree |
| Native source files (`*.c`, `*.cpp`, `*.cc`, `*.h`, `*.hpp`) | Not present | The `find` invocation in §3.2 returns zero files matching these extensions; the repository contains no C, C++, or header file at any path |
| Android build files (`*.gradle`, `AndroidManifest.xml`, `CMakeLists.txt`, `Android.mk`, `*.aar`, `*.apk`) | Not present | The `find` invocation in §3.2 returns zero files matching these patterns; there is no Gradle root build, no Gradle module build, no Android manifest, no native build descriptor, and no Android binary artifact in the repository |
| Firebase Crashlytics SDK (Java/Kotlin facade `com.google.firebase:firebase-crashlytics` or NDK companion `com.google.firebase:firebase-crashlytics-ndk`) | Not present | `[package.json]` declares no `dependencies` and no `devDependencies` (no `package.json` field for Crashlytics could even apply in a Node.js project — there is no Maven/Gradle coordinate to declare); `[package-lock.json]` (lockfileVersion 3) `packages` object contains only the root project entry; `[Tech Spec §3.3]` independently confirms zero open-source dependencies; the repository is a Node.js HTTP fixture, not an Android application |

The absence documented above is **complete and structural**. Not a single one of the canonical Crashlytics NDK architecture components has any representation in this repository's text source files, build files, or dependency manifests; and the repository does not even have the **substrate** that a Crashlytics NDK implementation would require — there is no Android project, no JVM build, no native build, and no shared-object loader infrastructure. The empirical finding is therefore not "Crashlytics is partially implemented" or "Crashlytics is stubbed" — it is "Crashlytics is wholly absent because this repository's nature is unrelated to Android crash reporting".

## 6. Controlling Constraints

Even if the introduction of Crashlytics NDK components into this repository were considered desirable, six controlling constraints from the Technical Specification and the repository's own preservation directive would individually prohibit such an introduction. Each constraint is listed below with its locator and the specific introduction it forecloses.

- `[README.md:L1-L2]` "test project for backprop integration. Do not touch!" — The repository's root README directly prohibits modifying any existing file. This directive predates and is reinforced by `[Tech Spec §5.5.2: C-001]` and forecloses **all 18 root-file modifications** that a Crashlytics integration would require (e.g., adding a `firebase-crashlytics-ndk` Maven coordinate to a Gradle file, adding `apply plugin: 'com.google.firebase.crashlytics'` to an Android module, adding `System.loadLibrary("crashlytics")` to an Application subclass).
- `[Tech Spec §5.5.2: C-001]` "Repository must remain unchanged" — Formalizes the README directive as a binding controlling constraint. Verifiable compliance is `git diff --name-status` against the pre-implementation baseline showing only `A` (added) entries under `docs/analysis/`.
- `[Tech Spec §5.5.2: C-002]` "Zero external npm dependencies" — Forecloses the npm-package route of introducing a JavaScript-side Crashlytics surface (e.g., `firebase`, `@react-native-firebase/crashlytics`, `cordova-plugin-firebase-crashlytics`). The constraint is verifiable: `[package.json]` declares no `dependencies` and no `devDependencies`; `[package-lock.json]` (lockfileVersion 3) carries no transitive tree.
- `[Tech Spec §5.5.2: C-003]` "Localhost-only network binding" — `[server.js:L3-L4]` binds to `127.0.0.1:3000`, which is structurally incompatible with the public Crashlytics reports endpoint (Crashlytics uploads HTTPS POSTs to a Firebase-hosted, publicly-routable endpoint). Introducing an outbound Crashlytics uploader would either violate this constraint or require a localhost-only test double that has no relationship to the real Crashlytics backend.
- `[Tech Spec §5.5.2: C-004]` "MIT License compliance" — Applies to all new content authored under this analysis. The Firebase Crashlytics Android SDK is licensed under the Apache License 2.0; introducing its compiled binary into this repository would create a multi-license artifact and would require notice/attribution under the Apache 2.0 redistribution terms `[NOTICE]`-style file, which is itself an additional file the repository cannot accept under `C-001`.
- `[Tech Spec §5.5.2: C-005]` "Single-file application architecture" — `[server.js]` is the single executable file in the repository. Introducing a Crashlytics NDK integration would require, at minimum, an Android application module, a native (C/C++) source tree, a Gradle build system, a CMake or Android.mk descriptor, an `AndroidManifest.xml`, and one or more Java/Kotlin classes — multiplying the executable file count by at least an order of magnitude and breaking the single-file architectural constraint.
- `[Tech Spec §5.6]` "Explicitly excluded capabilities" — independently excludes HTTPS/TLS, authentication, deployment, monitoring/APM, and CI/CD — each of which a real Crashlytics integration would require (HTTPS for the upload pipeline, authentication via the API key, deployment infrastructure for the Android application binary that would carry the SDK, monitoring of upload success rates, and CI/CD to publish symbol files for offline symbolication).

The constraints above are **independent** — each on its own forbids the introduction. Together they make the introduction structurally impossible in this fixture.

## 7. Conclusion and Recommendations

This report's findings can be summarized in three statements.

1. **What this report is.** This deliverable is an informational, evidence-grounded analysis report addressing the user prompt — "Analyze the Crashlytics NDK crash handling architecture including signal handlers, JNI bridges, and minidump generation" — against the supplied `hao-backprop-test` repository. The author searched the repository exhaustively for any indication of Crashlytics NDK content (recursive case-insensitive text-only grep over `*.js`, `*.json`, `*.md`, `*.java`, `*.txt`, `*.csv` files for the regex `crashlytics|firebase|ndk|signal_handler|sigaction|minidump|breakpad|crashpad|JNIEXPORT|JNICALL|jni\.h|backoff|retry|upload`, plus a `find` for native and Android file patterns), found nothing, and reports that empirical absence honestly rather than substituting findings from a different repository or paraphrasing the canonical Crashlytics architecture as if it were locally present. The reference-architecture section (§4) is included **only** as a conceptual frame against which the empirical absence (§5) can be measured; every conceptual claim in §4 is flagged `[inferred — industry-standard description, no direct repository source]` so that the reader cannot mistake the reference description for a finding about this repository.

2. **What the user should consider doing next.** If the user's intent was to analyze a Crashlytics-bearing repository — for example, the public `firebase/firebase-android-sdk` repository (which contains the Java/Kotlin facade, the NDK companion module, and the native Breakpad-derived minidump writer) — then that repository should be supplied and a fresh analysis should be performed against it. Re-targeting was not performed unilaterally by this deliverable because the AAP's honesty rule (`§0.7.4 — Methodological Rules`) and the scope exclusions (`§0.3.2`) forbid silent re-targeting; an explicit instruction from the user is required. If, alternatively, the user's intent was to verify that **this** repository is unrelated to Crashlytics NDK (for example as part of a fixture-validation pass), then this report provides exactly that verification with full citation provenance.

3. **Compliance summary.** No code changes have been made to the existing repository. All 18 root files (`README.md`, `package.json`, `package-lock.json`, `server.js`, `server - Copy.js`, `LoginTest.java`, `LoginTest - Copy.java`, `industry.csv`, `industry - Copy.csv`, `test.py.txt`, `test.py - Copy.txt`, `test.txt.txt`, `100Pages.pdf`, `100Pages - Copy.pdf`, `demo.jpg`, `demo - Copy.jpg`, `sample.doc`, `sample - Copy.doc`) remain bit-identical to their pre-implementation state. No npm package was added — `[package.json]` and `[package-lock.json]` remain bit-identical. No native source, no Android build file, no Crashlytics SDK, and no signal-handling code has been introduced. This complies with `[README.md:L1-L2]` "test project for backprop integration. Do not touch!", `[Tech Spec §5.5.2: C-001]` "Repository must remain unchanged", `[Tech Spec §5.5.2: C-002]` "Zero external npm dependencies", `[Tech Spec §5.5.2: C-003]` "Localhost-only network binding", `[Tech Spec §5.5.2: C-004]` "MIT License compliance", and `[Tech Spec §5.5.2: C-005]` "Single-file application architecture". The only artifacts introduced by this analysis effort live under the new `docs/analysis/` directory and are purely additive textual documentation.

> Related: See [`./crash-upload-retry-test-coverage.md`](./crash-upload-retry-test-coverage.md) for the test-coverage analysis of the (also-absent) crash upload and retry mechanisms, and [`./README.md`](./README.md) for the directory index.
