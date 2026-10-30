# Rebuilding Anaco 1.3.2

The source archive contains the browser extension, its local Native Messaging
companion and build inputs. It excludes development environments, personal test
artifacts, browser profiles and credentials. The add-on ZIP contains only the
contents of `extension/`; it does not include the native companion.

## Environment

The release build was prepared on Linux x86_64 with Node.js 26.10.0,
npm 11.19.1 and Python 3.14.7. CI also uses Node.js 22 and tests the companion
with Python 3.12 and 3.13, plus process and launcher tests on Linux, macOS
and Windows with Python 3.11 and 3.13. Extension generation only uses portable Node.js and
Python standard-library operations; no native compiler is required.

## Extension build

Run in the extracted source directory:

```sh
npm ci
npm run vendor
python3 scripts/i18n.py build
python3 scripts/i18n.py check
npm test
npm run lint
npm run build
```

The result is `dist/anaco-ob-1.3.2.zip`. Compare the names and bytes of its
uncompressed entries with the submitted add-on. ZIP timestamps may differ.
No signing key or environment secret is required.

`scripts/vendor.mjs` copies pinned, unmodified npm distributions and licenses
of marked 18.1.1 and DOMPurify 3.4.17 into `extension/vendor/`.
`scripts/i18n.py build` generates `extension/i18n-catalog.js` from the translation
JSON files. There is no first-party JavaScript bundler, transpiler, minifier or
obfuscator. Third-party source links and account-free testing instructions are
in `docs/amo/1.3.0-reviewer-notes.txt` (the previous AMO submission materials).
This release adds stable update checks and in-plugin companion updates. The
extension checks the public Mozilla and GitHub APIs daily (disable in Options).
Only version metadata is requested, without cookies or user content. The extension
update button opens the official AMO listing; Firefox handles installation and signing.
The native companion installs the official stable tagged Python package in a separate
virtual environment, verifies its version, then switches the Native Messaging launcher.
No remote code is loaded into the extension. See `docs/amo/1.3.2-reviewer-notes.txt`.

## Source archive

From the release checkout, run `python3 scripts/release_sources.py`. It packages
version-controlled build inputs and tests only, excluding local environments,
browser profiles, captures and credentials. The working tree must match the release
commit; untracked local presentation assets are not included.

## Local companion

The companion requires Python 3.11 or newer and has no runtime Python package
dependencies for manual captures. Install from this source archive:

```sh
python3 -m venv .review-venv
.review-venv/bin/python -m pip install .
.review-venv/bin/anaco-ob install --vault /absolute/path/to/test-vault
```

Create the test vault directory first. On Windows the executables are under
`.review-venv\Scripts\`. Confirm the vault profile in the extension's Options
before preparing a note. Choose the manual/no-AI mode to test without an account.
Optional PDF/media processing requires external tools; transcription uses a
separate Faster Whisper environment installed only on user request.

Existing users need to update the companion as well as the browser extension.
The pinned installation command is in README.md. The welcome-page
installer still follows main. Both retain local settings and captures. On Windows,
installation requires Windows PowerShell and .NET Framework to compile the
native launcher locally; the extension build does not need them.
