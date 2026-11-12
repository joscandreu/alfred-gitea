# MIGRATED to https://codefloe.com/pat-s/alfred-gitea

# alfred-gitea

- [alfred-gitea](#alfred-gitea)
  - [Installation](#installation)
  - [Usage](#usage)
    - [Quick Open](#quick-open)
    - [Starting fresh](#starting-fresh)
  - [Acknowledgment](#acknowledgment)
  - [Misc](#misc)

## Installation

Build the workflow from this repository and double-click the result to install it in Alfred:

```sh
./build.sh   # creates Gitea.alfredworkflow from ./source
```

1. Set your Gitea URL via `tea set url https://<host>` (only `https://` URLs are accepted).
2. Set your Gitea Access Token via `tea set token`.
   Press &#x23ce; without typing the token to enter it in a hidden dialog (recommended), or pass it directly: `tea set token <token>` (`tea set key` is an alias).
   The token is stored in the macOS Keychain and sent to Gitea in the `Authorization` header.
3. If your instance requires a client certificate, see [Client certificates (mutual TLS)](#client-certificates-mutual-tls).

The workflow calls the `/api/v1/repos/search` endpoint and will only list repos which are accessible via the given access token.

### Client certificates (mutual TLS)

Open the workflow in Alfred Preferences, click the `[x]` (Configure Workflow and Variables) button and set:

| Variable      | Value |
| ------------- | ----- |
| `client_cert` | Path to your client certificate in PEM format. The file may also contain the private key and intermediate certificates. |
| `client_key`  | Path to the PEM private key, if it is in a separate file. |
| `ca_bundle`   | Path to a PEM file with your company's CA certificate(s), if the Gitea server certificate is issued by a private CA. It is added to the system CAs. |

`~` is expanded. These variables are marked "don't export", so they are not included if you share the workflow.

If the private key is encrypted, store its passphrase in the Keychain with `tea set certpass` (a hidden dialog opens; submit an empty value to remove it).

If your certificate comes as a `.p12`/`.pfx` file, convert it to PEM first, e.g.:

```sh
openssl pkcs12 -in client.p12 -out ~/.config/gitea/client.pem   # key stays encrypted -> use `tea set certpass`
chmod 600 ~/.config/gitea/client.pem
```

Connection or certificate problems are shown as the first result of `tea <query>` ("Error updating project list").
Note that the repos are opened in your browser, which needs the client certificate itself (e.g. imported into the Keychain).

**Python3 and macOS > 12.3**

macOS 12.3 does not ship with a Python2 interpreter anymore, hence `alfred-gitea` versions < 2.0.0 will not work.
Please update to `alfred-gitea` >= 2.0.0.

## Usage

`tea <query>` shows all repos using the repos slug `owner/repo`
The next menu let's you make a selection which subpart of the repo to open:

- Code (repo home)
- Issues
- Pull Requests
- Releases
- Wiki
- Projects
- Settings

The workflow learns from usage and will sort the returned results by this criteria.

### Quick Open

If you hold the &#x2325; (`option`) key and then hit &#x23ce; (`return`), the subfolder selection will be skipped and the repository will be opened directly.
This behavior can also be set as the default by setting variable `quick_open` to `true` in the Alfred workflow options.
Note however that this will not allow selecting a specific location (repo, settings, etc.) anymore.

<p style="text-align:center">
<img alt="alfred-gitea-gif" src="https://media.giphy.com/media/GlHoA8FEovaNgkUlrj/giphy.gif"/>
</p>

### Starting fresh

If you want to reset the learned behavior or switch to a new Gitea instance, call `tea reset`.
This will delete the cache, the URL and the secrets stored in the Keychain (access token and client key passphrase).
The client certificate variables are kept.

If you **only** want to delete the repo cache, call `tea clearcache`.
This will keep the URL and API key set and only invalidate the repo cache.

## Security notes

- Self-update from the upstream GitHub repository is disabled, as it would download and install unsigned code and overwrite this customised version. Rebuild with `./build.sh` instead.
- Only `https://` Gitea URLs are accepted, TLS certificates and host names are always verified, and TLS < 1.2 is refused.
- Repository links are only shown if they point to the configured Gitea instance.

## Acknowledgment

- Inspired by [alfred-gitlab](https://github.com/lukewaite/alfred-gitlab)
- Python2 version was initially powered by the [Alfred-Workflow](https://www.deanishe.net/alfred-workflow/index.html) python module
- Python3 conversion was adapted from [TribuneX/alfred-gitlab](https://github.com/TribuneX/alfred-gitlab)
- Webscraping functionality comes from [slingamn/mureq](https://github.com/slingamn/mureq)

## Misc

- [How to add dynamic repo thumbnails in alfred-workflow](https://github.com/deanishe/alfred-workflow/issues/106#issuecomment-737505965)
- Dev info: The Gitea API does not return `x-next-page` and `x-page` headers, therefore the total number of pages needs to be calculated on the fly in every run

**What about repo avatars?**

There is in fact a working solution for repo avatars.
However it requires the download of all avatars on each run and a subsequent thumbnail conversion.
This adds a delay of at least two seconds until the first match appears in Alfred.
Hence I decided to use fixed repo icons.
