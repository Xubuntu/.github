# Team roster

The org profile ([`profile/README.md`](../profile/README.md)) lists our public teams and their members. GitHub doesn't show org teams to non-members, so a workflow generates this list.

- **Script:** [`.github/scripts/render_teams.py`](../.github/scripts/render_teams.py). It uses only the Python 3 standard library.
- **Workflow:** [`.github/workflows/update-teams.yml`](../.github/workflows/update-teams.yml). It runs every Monday, when started by hand, and when the script or workflow changes on `main`.

The script rewrites only the text between `<!-- TEAMS:START -->` and `<!-- TEAMS:END -->`. Anything outside those markers is safe to edit by hand. It adds no timestamp, so the workflow commits only when the roster actually changes.

## What gets shown

- **Teams:** only teams with *visible* privacy. Secret teams are skipped. Child teams appear as subheadings under their parent.
- **Team members:** only people whose org membership is public. Private members aren't named. The workflow runs the script with `--show-private-count`, so each team ends with "+N private members" instead. Remove that flag from the workflow to hide the count.
- **Parent team members:** GitHub counts child-team members as members of the parent team, so they appear in both lists.

### Making your membership public

Your membership is private by default. To appear in the roster:

1. Go to **github.com/orgs/Xubuntu/people**.
2. Find your name and change **Private** to **Public**.

The roster picks up the change on its next run.

## One-time setup

The workflow's built-in `GITHUB_TOKEN` can't read team membership, so a small GitHub App owned by the org provides a token for reading teams. The `GITHUB_TOKEN` is used only to commit.

### 1. Create the GitHub App

An org owner does this.

1. Go to **github.com/organizations/Xubuntu/settings/apps** and select **New GitHub App**.
2. Fill in the form:
   - **Name:** for example, `Xubuntu Team Roster`.
   - **Homepage URL:** `https://github.com/Xubuntu`.
   - **Webhook:** uncheck **Active**.
   - **Permissions:** under **Organization permissions**, set **Members** to **Read-only**. Leave every other permission at *No access*. The required *Metadata: read* is added automatically.
   - **Where can this GitHub App be installed?** Choose **Only on this account**.
3. Select **Create GitHub App**.
4. On the app's settings page, note the **Client ID**, which looks like `Iv23li…`. The numeric **App ID** also works.
5. Under **Private keys**, select **Generate a private key**. A `.pem` file downloads.

### 2. Install the app on the org

1. On the app's settings page, select **Install App**, then choose **Xubuntu**.
2. Choose **Only select repositories** and pick `Xubuntu/.github`.

Members permission is org-wide, so the app can read teams no matter which repositories you select.

### 3. Add the repository secrets

In **Xubuntu/.github → Settings → Secrets and variables → Actions**, add these secrets:

| Secret | Value |
| --- | --- |
| `TEAMS_APP_ID` | The app's Client ID (or numeric App ID) |
| `TEAMS_APP_PRIVATE_KEY` | The full contents of the `.pem` file, including the `BEGIN`/`END` lines |

After you add the key, delete the downloaded `.pem` file. Never commit it.

### 4. Run the workflow

Go to **Actions → Update team roster → Run workflow**. If the roster changed, the run commits "Update team roster" as `github-actions[bot]`.

## Running locally

You need a token that can read org team membership. Either of these works:

- **GitHub CLI:** run `gh auth token`, if you're an org member logged in with the `read:org` scope.
- **Personal access token:** a fine-grained PAT for the Xubuntu org with **Members: read**.

Run from the repository root:

```sh
# Print the generated section without changing any files
GH_TOKEN="$(gh auth token)" python3 .github/scripts/render_teams.py --dry-run

# Include "+N private members" in the output
GH_TOKEN="$(gh auth token)" python3 .github/scripts/render_teams.py --dry-run --show-private-count

# Update profile/README.md in place
GH_TOKEN="$(gh auth token)" python3 .github/scripts/render_teams.py
```

The script also accepts `--org` and `--readme`. Run it with `--help` for details.

## Troubleshooting

- **`HTTP 403` or `HTTP 404` on `/orgs/Xubuntu/teams`:** the app doesn't have **Members: read**, or isn't installed on the org. If you added the permission after installing the app, an org owner must accept the updated permissions under **Org settings → GitHub Apps**.
- **`HTTP 401`:** the token is invalid or expired. Check both secrets.
- **The token step fails:** check that `TEAMS_APP_PRIVATE_KEY` contains the whole `.pem` file and that the app is installed on `Xubuntu/.github`.
- **Someone is missing from the roster:** their org membership is private. See [Making your membership public](#making-your-membership-public).
- **The weekly run stopped:** in public repositories, GitHub disables scheduled workflows after 60 days without repository activity. The workflow commits only when the roster changes, so don't count on its own commits to keep the schedule alive. To turn it back on, go to **Actions → Update team roster** and select **Enable workflow**, or run it by hand with **Run workflow**. Any push to the repository also resets the 60-day timer.
