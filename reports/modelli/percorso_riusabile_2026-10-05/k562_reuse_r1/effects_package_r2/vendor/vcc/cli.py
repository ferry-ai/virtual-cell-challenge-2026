"""Top-level Click entry point for the vcc CLI.

The root command group, the shared ``--json`` output toggle, and every
user-facing command (login, whoami, prep, sample, submit, status, datasets,
skill) are wired up here.
"""

from __future__ import annotations

import json
import sys
from typing import TYPE_CHECKING

import click

from vcc._scores import SCORE_FIELDS as _SCORE_FIELDS
from vcc._version import version_info

if TYPE_CHECKING:  # import for type checkers only — never at runtime, so
    from vcc.prep import PrepResult  # `vcc --help` still doesn't load anndata
    from vcc.sample import SampleResult


def _print_version(as_json: bool) -> None:
    info = version_info()
    if as_json:
        click.echo(json.dumps(info))
        return
    click.echo(f"vcc {info['vcc']}")
    click.echo(f"Python {info['python']} ({info['platform']})")
    click.echo(f"build: {info['channel']} · endpoint: {info['endpoint']}")


def _version_flag_callback(ctx: click.Context, param: click.Parameter, value: bool) -> None:
    # `--version` flag: print and exit before any subcommand runs. Honors the
    # group-level --json flag regardless of its position on the command line —
    # --json is eager and --version is not, so Click always assigns json_output
    # into ctx.params before this callback fires (`vcc --version --json` works too).
    if not value or ctx.resilient_parsing:
        return
    _print_version(bool(ctx.params.get("json_output")))
    ctx.exit()


@click.group(
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.option(
    "--json",
    "json_output",
    is_flag=True,
    is_eager=True,
    help="Emit machine-readable JSON instead of human-readable text.",
)
@click.option(
    "--profile",
    default=None,
    help="Named credential profile [env: VCC_PROFILE].",
)
@click.option(
    "--endpoint",
    default=None,
    help="Base URL of the VCC site to talk to [env: VCC_ENDPOINT].",
)
@click.option(
    "--version",
    is_flag=True,
    expose_value=False,
    callback=_version_flag_callback,
    help="Show the vcc version and exit.",
)
@click.pass_context
def cli(ctx: click.Context, json_output: bool, profile: str | None, endpoint: str | None) -> None:
    """vcc — submit predictions to the Virtual Cell Challenge.

    Run `vcc version` for version details, or `vcc COMMAND --help` for a command.
    """
    # Stash shared state so subcommands can read it via `ctx.obj`.
    ctx.ensure_object(dict)
    ctx.obj["json"] = json_output
    ctx.obj["profile"] = profile
    ctx.obj["endpoint"] = endpoint


@cli.command()
@click.option(
    "--json",
    "json_output",
    is_flag=True,
    help="Emit machine-readable JSON instead of human-readable text.",
)
@click.pass_context
def version(ctx: click.Context, json_output: bool) -> None:
    """Print the vcc version."""
    # Accept --json either before the subcommand (group flag, stashed in ctx.obj)
    # or after it (this command's own flag), so both positions work.
    _print_version(bool(ctx.obj.get("json")) or json_output)


def _echo_prep_result(result: PrepResult, as_json: bool) -> None:
    """Render a prep result. `PrepResult` is a type-checking-only import, so this
    stays fully typed without pulling anndata into the CLI's import path."""
    if as_json:
        click.echo(json.dumps(result.to_dict()))
        return
    click.echo("✓ dry run — no .vcc written" if result.dry_run else "✓ prep complete")
    click.echo(f"  input:         {result.input}")
    click.echo(f"  output:        {result.output if result.output else '(dry run)'}")
    click.echo(f"  cells:         {result.n_cells}")
    click.echo(f"  genes:         {result.n_genes}  (encoding: float{result.encoding})")
    click.echo(f"  perturbations: column '{result.pert_col}' → '{result.output_pert_col}'")
    if result.cells_per_context:
        summary = ", ".join(f"{c}={n}" for c, n in sorted(result.cells_per_context.items()))
        click.echo(f"  contexts:      column '{result.context_col}' → {summary}")
    click.echo(f"  targets:       {'verified against the official list' if result.verified_targets else 'NOT verified'}")
    click.echo(f"  normalization: {result.normalization}")
    if result.dropped:
        click.echo(f"  dropped:       {', '.join(result.dropped)}")
    for note in result.notes:
        click.echo(f"  note:          {note}")


@cli.command()
@click.argument("input_arg", metavar="[INPUT.h5ad]", required=False, type=click.Path())
@click.option("-i", "--input", "input_opt", type=click.Path(), help="Path to the input .h5ad (alternative to the positional argument).")
@click.option("-g", "--genes", type=click.Path(), help="Headerless CSV of expected gene symbols, in order.")
# No short flag: `-p` is already --pert-col on this command (and --perts on `sample`).
@click.option("--perts", type=click.Path(), default=None, help="pert_counts.csv from the controls bundle — the official perturbation list, checked per context.")
@click.option("--verify-targets/--no-verify-targets", default=True, show_default=True, help="Check each context predicts exactly its official perturbations. Needs --perts.")
@click.option("--check-cell-counts/--no-check-cell-counts", default=True, show_default=True, help="Require each perturbation to have exactly the official number of cells.")
@click.option("--cells-per-pert", type=int, default=400, show_default=True, help="Cells required per perturbation (the panel's count). An n_cells column in --perts wins over it; -1 means no built-in expectation.")
@click.option("-o", "--output", type=click.Path(), help="Path to write the .vcc [default: <input>.prep.vcc].")
@click.option("-p", "--pert-col", default="target_gene", show_default=True, help="Input column naming perturbations.")
@click.option("-c", "--celltype-col", default=None, help="Input column naming cell type (optional).")
@click.option("-n", "--ntc-name", default="non-targeting", show_default=True, help="Negative-control label expected in the perturbation column.")
@click.option("-P", "--output-pert-col", default="target_gene", show_default=True, help="Perturbation column name in the output.")
@click.option("-C", "--output-celltype-col", default="celltype", show_default=True, help="Cell-type column name in the output.")
@click.option("--context-col", default="context", show_default=True, help="Input column naming the cell context (A/B/C), as in the control files.")
@click.option("--contexts", default="A,B,C", show_default=True, help="Comma-separated contexts a submission must cover; empty disables the check.")
@click.option("-e", "--encoding", type=click.Choice(["32", "64"]), default="32", show_default=True, help="Float bit width for X.")
@click.option("--allow-discrete", is_flag=True, help="Legacy: with --no-require-counts, keep integer counts as-is instead of log-normalizing.")
@click.option("--require-counts/--no-require-counts", default=True, show_default=True, help="Require raw integer counts (2026 scores in counts space). --no-require-counts restores log-normalization.")
@click.option("--reject-controls/--allow-controls", default=True, show_default=True, help="Reject submitted control cells (scoring uses the held-out controls, never yours).")
@click.option("--expected-gene-dim", type=int, default=18533, show_default=True, help="Expected gene dimension; -1 disables the check.")
@click.option("--max-cell-dim", type=int, default=400000, show_default=True, help="Maximum cell count; -1 disables the cap.")
@click.option("--max-nnz", type=int, default=None, help="Maximum nonzero values (density cap); -1 disables the cap.  [default: the scoring hardware's limit]")
@click.option("--max-counts-per-cell", type=int, default=1000000, show_default=True, help="Maximum per-cell count total (sum over genes); -1 disables the cap.")
@click.option("--dry-run", is_flag=True, help="Validate and report what prep would do, without writing output.")
@click.option("-f", "--force", is_flag=True, help="Overwrite the output file if it already exists.")
@click.option("--json", "json_output", is_flag=True, help="Emit machine-readable JSON instead of human-readable text.")
@click.pass_context
def prep(
    ctx: click.Context,
    input_arg: str | None,
    input_opt: str | None,
    genes: str | None,
    perts: str | None,
    verify_targets: bool,
    check_cell_counts: bool,
    cells_per_pert: int,
    output: str | None,
    pert_col: str,
    celltype_col: str | None,
    ntc_name: str,
    output_pert_col: str,
    output_celltype_col: str,
    context_col: str,
    contexts: str,
    encoding: str,
    allow_discrete: bool,
    require_counts: bool,
    reject_controls: bool,
    expected_gene_dim: int,
    max_cell_dim: int,
    max_nnz: int | None,
    max_counts_per_cell: int,
    dry_run: bool,
    force: bool,
    json_output: bool,
) -> None:
    """Validate, slim, normalize, and package an .h5ad into a .vcc.

    Native reimplementation of `cell-eval prep` — no network calls, no cell-eval
    dependency. Catches locally the same errors the server would reject.
    """
    as_json = bool(ctx.obj.get("json")) or json_output

    # Resolve the input from either the positional argument or -i/--input.
    if input_arg and input_opt:
        raise click.UsageError("Provide the input once — either as the positional argument or via -i/--input, not both.")
    input_path = input_arg or input_opt
    if not input_path:
        raise click.UsageError("Missing input .h5ad. Usage: vcc prep INPUT.h5ad -g GENES.csv")

    if not genes:
        raise click.UsageError(
            "Missing gene list. Pass -g/--genes with the official gene_names.csv. "
            "Get it from the controls bundle: `vcc datasets download controls` "
            "(gene_names.csv is inside the downloaded zip)."
        )

    from vcc import prep as prep_mod  # lazy: pulls in anndata/scipy only when prep runs

    try:
        result = prep_mod.run_prep(
            input_path=input_path,
            genes_path=genes,
            output_path=output,
            perts_path=perts,
            verify_targets=verify_targets,
            check_cell_counts=check_cell_counts,
            cells_per_pert=None if cells_per_pert == -1 else cells_per_pert,
            pert_col=pert_col,
            celltype_col=celltype_col,
            ntc_name=ntc_name,
            output_pert_col=output_pert_col,
            output_celltype_col=output_celltype_col,
            context_col=context_col,
            output_context_col=context_col,
            required_contexts=tuple(c.strip() for c in contexts.split(",") if c.strip()),
            encoding=int(encoding),
            allow_discrete=allow_discrete,
            require_counts=require_counts,
            reject_controls=reject_controls,
            expected_gene_dim=None if expected_gene_dim == -1 else expected_gene_dim,
            max_cell_dim=None if max_cell_dim == -1 else max_cell_dim,
            # None means "use the server's number", which is the default and the only
            # value that cannot disagree with it. -1 is the explicit opt-out.
            max_nnz=(
                prep_mod.MAX_NNZ if max_nnz is None
                else (None if max_nnz == -1 else max_nnz)
            ),
            max_counts_per_cell=None if max_counts_per_cell == -1 else max_counts_per_cell,
            dry_run=dry_run,
            force=force,
        )
    except prep_mod.PrepError as exc:
        if as_json:
            click.echo(json.dumps({"error": str(exc)}), err=True)
        else:
            click.echo(f"vcc prep: {exc}", err=True)
        ctx.exit(1)

    _echo_prep_result(result, as_json)


def _echo_sample_result(result: SampleResult, as_json: bool) -> None:
    """Render a sample result. `SampleResult` is a type-checking-only import, so
    this stays typed without pulling anndata into the CLI's import path."""
    if as_json:
        click.echo(json.dumps(result.to_dict()))
        return
    click.echo("✓ sample written (.vcc)" if result.is_vcc else "✓ sample written (.h5ad)")
    click.echo(f"  output:        {result.output}")
    click.echo(f"  cells:         {result.n_cells}")
    click.echo(f"  genes:         {result.n_genes}")
    click.echo(f"  perturbations: {result.n_perts}  (+ non-targeting: {result.ntc_cells} cells)")
    # Always shown, generated or passed: without it a randomly-seeded sample could
    # not be reproduced, and two testers comparing scores need to see that their
    # inputs differ.
    click.echo(f"  seed:          {result.seed}  (pass --seed {result.seed} to reproduce)")
    for note in result.notes:
        click.echo(f"  note:          {note}")
    if result.is_vcc:
        click.echo("")
        click.echo("Submit it with:")
        click.echo(f'  vcc submit {result.output} -m "sample"')


@cli.command()
@click.option("-g", "--genes", type=click.Path(), required=True, help="Headerless CSV of gene symbols (the official VCC gene list, from `vcc datasets download`).")
@click.option("-o", "--output", type=click.Path(), help="Where to write the sample [default: sample.vcc, or sample.h5ad with --h5ad].")
@click.option("-p", "--perts", type=click.Path(), required=True, help="pert_counts.csv from the controls bundle — the official perturbation list. Required: a sample built from anything else is rejected by scoring.")
@click.option("--cells-per-pert", type=int, default=None, help="Cells per perturbation [default: 400 with --full, 5 with --no-full]. An n_cells column in --perts still wins.")
@click.option("--full/--no-full", default=True, show_default=True, help="Give each perturbation the official 400 cells. --no-full makes a small, DELIBERATELY INVALID file that scoring will reject — upload-path testing only.")
@click.option("--ntc-cells", type=int, default=None, help="Non-targeting control cell count [default: --cells-per-pert]. Only for the legacy --contexts '' shape.")
@click.option("--genes-per-cell", type=int, default=300, show_default=True, help="Nonzero genes per cell (controls sparsity and file size).")
@click.option("--context-col", default="context", show_default=True, help="Context column name to write into the sample.")
@click.option("--contexts", default="A,B,C", show_default=True, help="Comma-separated contexts the sample must cover; empty disables contexts.")
@click.option("--max-cell-dim", type=int, default=400000, show_default=True, help="Maximum total cells; -1 disables the cap (raise it for a very large --full sample).")
@click.option(
    "--seed",
    type=int,
    default=None,
    help=(
        "RNG seed. Omitted, each run generates a different sample (and prints the "
        "seed it used); pass that value back to reproduce one exactly."
    ),
)
@click.option("--h5ad", "as_h5ad", is_flag=True, help="Write a raw .h5ad instead of packaging a .vcc.")
@click.option("-f", "--force", is_flag=True, help="Overwrite the output file if it already exists.")
@click.option("--json", "json_output", is_flag=True, help="Emit machine-readable JSON instead of human-readable text.")
@click.pass_context
def sample(
    ctx: click.Context,
    genes: str,
    output: str | None,
    perts: str,
    cells_per_pert: int | None,
    full: bool,
    ntc_cells: int | None,
    genes_per_cell: int,
    context_col: str,
    contexts: str,
    max_cell_dim: int,
    seed: int | None,
    as_h5ad: bool,
    force: bool,
    json_output: bool,
) -> None:
    """Generate a random, valid dummy prediction for testing `vcc submit`.

    Builds synthetic random counts over the given gene list — one cell group per
    perturbation — and packages a submittable .vcc (same format as `vcc prep`).
    The result is minimal but *complete*: every official perturbation from
    `pert_counts.csv`, in every context, with exactly the 400 cells each the panel
    uses, so scoring accepts it. The values are noise, so it is for pipeline testing
    (upload → scoring),
    NOT for scoring well.

    Both -g and -p come from `vcc datasets download controls`.
    """
    as_json = bool((ctx.obj or {}).get("json")) or json_output
    out = output or ("sample.h5ad" if as_h5ad else "sample.vcc")

    from vcc import sample as sample_mod  # lazy: pulls in anndata/scipy only when run
    from vcc.prep import PrepError

    try:
        result = sample_mod.run_sample(
            genes_path=genes,
            output_path=out,
            perts_path=perts,
            cells_per_pert=cells_per_pert,
            full=full,
            ntc_cells=ntc_cells,
            genes_per_cell=genes_per_cell,
            context_col=context_col,
            contexts=tuple(c.strip() for c in contexts.split(",") if c.strip()),
            max_cell_dim=None if max_cell_dim == -1 else max_cell_dim,
            seed=seed,
            as_h5ad=as_h5ad,
            force=force,
        )
    except (sample_mod.SampleError, PrepError) as exc:
        _fail(ctx, str(exc), as_json)
        return  # unreachable — _fail exits — but keeps type-checkers happy

    _echo_sample_result(result, as_json)


def _auth_context(
    ctx: click.Context,
    endpoint_override: str | None = None,
    profile_override: str | None = None,
):
    """Resolve (profile, endpoint, stored_state) for an auth-aware command.

    Command-level --profile/--endpoint win over the group-level ones, so both
    `vcc --endpoint X whoami` and `vcc whoami --endpoint X` work.
    """
    from vcc import auth, config

    # ctx.obj is populated by the group callback, but guard anyway: a command
    # invoked directly (tests, programmatic use) can arrive with obj unset.
    obj = ctx.obj or {}
    profile = config.resolve_profile(profile_override or obj.get("profile"))
    state = auth.read_profile_state(profile)
    explicit = endpoint_override or obj.get("endpoint")
    try:
        endpoint = config.resolve_endpoint(explicit, state.get("endpoint"))
    except config.ConfigError as exc:
        # ClickException (exit 1), not UsageError (exit 2): the bad endpoint may come
        # from VCC_ENDPOINT or a stored value, not a mistyped flag — so a "Try --help"
        # usage hint would misdirect. The message itself is already actionable.
        raise click.ClickException(str(exc)) from exc
    return profile, endpoint, state


def _fail(ctx: click.Context, message: str, as_json: bool, *, code: str | None = None) -> None:
    """Emit an error in the requested format and exit non-zero."""
    if as_json:
        payload: dict[str, object] = {"error": message}
        if code:
            payload["code"] = code
        click.echo(json.dumps(payload), err=True)
    else:
        click.echo(f"vcc: {message}", err=True)
    ctx.exit(1)


# _SCORE_FIELDS (imported from vcc._scores at the top) is the single source shared
# with `vcc submit --wait` so the labels/keys can't drift. --json emits raw keys.
#
# The six 2026 metrics carry a short name as well as a label, and both are printed —
# "Perturbation discrimination pds" — because the short form is what the leaderboard
# uses for its column headers, and the Evaluation page and the score email already
# name them both ways. Rows with no column of their own (rank, Overall, the legacy
# metrics, the stamp) have an empty short name and print the label alone.
def _echo_scores(data: dict) -> bool:
    """Print any present score fields with friendly labels. Returns True if any shown."""
    present = [
        (f"{label} {short}" if short else label, data[key])
        for key, label, short in _SCORE_FIELDS
        if data.get(key) is not None
    ]
    if not present:
        return False
    width = max(len(label) for label, _ in present)
    for label, value in present:
        click.echo(f"  {label + ':':<{width + 1}} {value}")
    return True


def _echo_error_info(err: object, *, width: int = 10, indent: str = "  ") -> bool:
    """Print a failed entry's server-side error, in full. Returns True if shown.

    The scoring job stores the SAME string it emails (it builds one
    `error_message` and hands it to both), and that string is multi-line — a
    header, an indented list of offending perturbations, then a "do this instead"
    line. Printed with a plain f-string only the first line landed under the
    label and the rest fell back to column 0, so the terminal showed a mangled
    version of what the email showed cleanly. Indent every line, continuations
    aligned under the first, so the two finally match.

    `width` is the caller's label column — the two call sites align to different
    blocks ("entry:/model:/status:" vs "final status:").
    """
    if isinstance(err, dict):
        message = err.get("error_message")
        timestamp = err.get("timestamp")
    else:
        message, timestamp = (err or None), None
    if not message:
        return False

    lines = str(message).splitlines() or [str(message)]
    head, *rest = lines
    click.echo(f"{indent}{'error:':<{width}}{head}")
    pad = indent + " " * width
    for line in rest:
        click.echo(f"{pad}{line.strip()}")
    if timestamp:
        click.echo(f"{indent}{'failed:':<{width}}{timestamp}")
    return True


def _identity_lines(me: dict, *, endpoint: str, profile: str, extra: list[str] | None = None) -> list[str]:
    """Render an identity block shared by `login` and `whoami`."""
    from vcc.config import credentials_url

    lines = [
        f"  account:  {me.get('email') or '(unknown)'}",
    ]
    display = me.get("display_name") or me.get("name")
    if display:
        lines.append(f"  name:     {display}")
    if me.get("organization"):
        lines.append(f"  org:      {me['organization']}")
    team = me.get("team_name") or me.get("team_id")
    lines.append(f"  team:     {team if team else '(none)'}")
    lines.append(f"  endpoint: {endpoint}")
    lines.append(f"  profile:  {profile}")
    if extra:
        lines.extend(extra)

    blockers = me.get("blockers") or []
    if me.get("can_submit"):
        lines.append("  status:   ready to submit")
    else:
        lines.append("  status:   NOT able to submit yet")
        explain = {
            "account_not_approved": "your account is awaiting approval by the VCC team",
            "identity_not_verified": "identity verification is incomplete — finish it in the web app",
            "no_team": "you are not on a team yet — create or join one in the web app",
            "pending_team_invites": "a teammate has not yet accepted/declined their invitation",
        }
        for blocker in blockers:
            lines.append(f"            • {explain.get(blocker, blocker)}")
        if blockers:
            lines.append(f"            see {credentials_url(endpoint).replace('/credentials', '')}")
    return lines


def _stdin_is_tty() -> bool:
    """Whether stdin is an interactive terminal (factored out so tests can override)."""
    import sys

    return sys.stdin.isatty()


def _read_token_interactive(ctx: click.Context, as_json: bool) -> str:
    """Prompt for a token, but only when that can actually work (AR8)."""
    if as_json or not _stdin_is_tty():
        _fail(
            ctx,
            "No API token provided and cannot prompt (not a terminal). "
            "Set VCC_TOKEN, or pipe the token: `vcc login --token-stdin < token.txt`.",
            as_json,
            code="no_token",
        )
    # hide_input keeps the token off the screen (AR5).
    return click.prompt("Paste your VCC API token", hide_input=True, err=True).strip()


@cli.command()
@click.option("--token", "token_opt", default=None, help="The API token. Visible in your shell history and process list — prefer --token-stdin.")
@click.option("--token-stdin", is_flag=True, help="Read the API token from stdin (one line). Best for piping from a secret manager.")
@click.option("--endpoint", "endpoint_opt", default=None, help="Base URL to log in against (remembered for this profile).")
@click.option("--store-plaintext", is_flag=True, help="If no secure OS keychain exists, save the token to a 0600 file instead of refusing.")
@click.option("--no-store", is_flag=True, help="Validate the token but store nothing (use VCC_TOKEN each run).")
@click.option("--json", "json_output", is_flag=True, help="Emit machine-readable JSON instead of human-readable text.")
@click.pass_context
def login(
    ctx: click.Context,
    token_opt: str | None,
    token_stdin: bool,
    endpoint_opt: str | None,
    store_plaintext: bool,
    no_store: bool,
    json_output: bool,
) -> None:
    """Authenticate with a VCC API token.

    Tokens are created in the web app on your Credentials page — the CLI cannot
    mint one (generating a token there revokes any previous token). Provide it
    via --token-stdin, --token, or the VCC_TOKEN environment variable.
    """
    import os

    from vcc import api, auth
    from vcc.config import TOKEN_PREFIX, credentials_url

    as_json = bool(ctx.obj.get("json")) or json_output
    profile, endpoint, _ = _auth_context(ctx, endpoint_opt)

    if token_opt and token_stdin:
        raise click.UsageError("Use either --token or --token-stdin, not both.")

    # Token source precedence, mirroring §5.2.1 — with one exception: an
    # *interactive* `vcc login` prefers the prompt over VCC_TOKEN. A person running
    # it means "let me enter a token"; silently reusing an ambient VCC_TOKEN (which
    # may be stale/revoked) would just re-validate it and trap them with no way to
    # log in a fresh one. Non-interactive (CI/headless) still falls back to env.
    env_token = os.environ.get("VCC_TOKEN")
    source = "flag"
    if token_stdin:
        token = click.get_text_stream("stdin").readline().strip()
        if not token:
            _fail(ctx, "No token received on stdin.", as_json, code="no_token")
    elif token_opt:
        token = token_opt.strip()
    elif env_token and (as_json or not _stdin_is_tty()):
        # Non-interactive (CI / headless): use VCC_TOKEN.
        token, source = env_token.strip(), "env"
    elif env_token:
        # Interactive with VCC_TOKEN set: refuse to guess. Using it silently hides a
        # stale/revoked token (traps re-login); prompting silently would hang pty
        # automation that expects the env token. Tell the user which they want.
        _fail(
            ctx,
            "VCC_TOKEN is set in your environment — every command already uses it, so you "
            "don't need `vcc login`.\n"
            "To log in a DIFFERENT token: run `unset VCC_TOKEN` first, or pass it explicitly "
            "with `--token-stdin` (or `--token`).",
            as_json,
            code="env_token_set",
        )
    else:
        token, source = _read_token_interactive(ctx, as_json), "prompt"

    if not token.startswith(TOKEN_PREFIX):
        _fail(
            ctx,
            f"That does not look like a VCC API token (expected it to start with '{TOKEN_PREFIX}').\n"
            f"Copy the token shown once at {credentials_url(endpoint)}.",
            as_json,
            code="malformed_token",
        )

    try:
        me = api.get_me(endpoint, token)
    except api.ApiError as exc:
        _fail(ctx, str(exc), as_json, code=exc.code)

    # An env-provided token is transient by contract — never persist it (§5.2.4).
    storage: str = "none"
    store_note: list[str] = []
    if no_store:
        # ONE line for --no-store. The token and the profile state are two
        # different things not written, but reporting them separately printed two
        # near-identical `stored:` lines that read as a contradiction (#381).
        store_note.append("  stored:   no — nothing written to disk (--no-store)")
    elif source == "env":
        storage = "none"
        store_note.append("  stored:   no (token came from VCC_TOKEN; it is never written to disk)")
    else:
        try:
            storage = auth.store_token(profile, token, allow_plaintext=store_plaintext)
        except auth.InsecureStoreError as exc:
            _fail(ctx, str(exc), as_json, code="insecure_store")
        store_note.append(
            "  stored:   OS keychain" if storage == "keyring" else "  stored:   0600 file (plaintext)"
        )

    if not no_store:
        # --no-store means nothing lands on disk. The profile state isn't the
        # token, but it does hold the account email, name, organization and the
        # masked token — writing it would break the flag's contract. The single
        # `stored:` line above already reports that; don't add a second one.
        auth.write_profile_state(
            profile,
            {
                "endpoint": endpoint,
                "identity": me,
                "token_storage": storage,
                "masked_token": auth.redact(token),
            },
        )

    if as_json:
        click.echo(json.dumps({"ok": True, "profile": profile, "endpoint": endpoint, "storage": storage, "identity": me}))
        return

    click.echo(f"✓ logged in as {me.get('email')}")
    for line in _identity_lines(me, endpoint=endpoint, profile=profile, extra=store_note):
        click.echo(line)
    if storage == "file":
        click.echo(
            "  warning:  no secure OS keychain was available, so the token is stored "
            "in plaintext (0600). On shared machines prefer VCC_TOKEN."
        )


@cli.command()
@click.option("--endpoint", "endpoint_opt", default=None, help="Base URL to query (overrides the profile's stored endpoint).")
@click.option("--profile", "profile_opt", default=None, help="Credential profile to inspect.")
@click.option("--json", "json_output", is_flag=True, help="Emit machine-readable JSON instead of human-readable text.")
@click.pass_context
def whoami(ctx: click.Context, endpoint_opt: str | None, profile_opt: str | None, json_output: bool) -> None:
    """Show the authenticated account, team, and whether you can submit."""
    from vcc import api, auth

    as_json = bool(ctx.obj.get("json")) or json_output
    profile, endpoint, state = _auth_context(ctx, endpoint_opt, profile_opt)

    try:
        resolved = auth.resolve_token(profile)
    except auth.AuthError as exc:
        _fail(ctx, str(exc), as_json, code="not_logged_in")

    try:
        me = api.get_me(endpoint, resolved.token)
        cached = False
        if resolved.source != "env":
            # Refresh the cache so a later offline `whoami` reflects today's
            # approval/team state rather than whatever was true at login.
            # Skipped for VCC_TOKEN: that path promises to leave nothing on disk,
            # and writing here would quietly break it (see --no-store).
            auth.write_profile_state(profile, {"identity": me})
    except api.ApiError as exc:
        # AR3: fall back to the cached identity when the network is the problem.
        # An explicit auth rejection (revoked/expired) must still be surfaced.
        # The cache is only valid for the endpoint it was captured from — showing
        # a prod identity while the user asked about staging (or a typo'd host)
        # would be actively misleading, so require the endpoint to match.
        # Gate on `status is None` — i.e. the request never got an HTTP reply at
        # all. `code is None` was too loose: an HTTP error whose body carries no
        # machine-readable code (a 500 HTML page, a proxy 502) also has code None,
        # and falling back there could print a stale "ready to submit" while the
        # server was actually rejecting us.
        cached_identity = state.get("identity")
        cached_endpoint = state.get("endpoint")
        if (
            exc.status is None
            and isinstance(cached_identity, dict)
            and cached_endpoint
            and endpoint == cached_endpoint
        ):
            me, cached = cached_identity, True
        else:
            _fail(ctx, str(exc), as_json, code=exc.code)

    if as_json:
        click.echo(json.dumps({
            "profile": profile, "endpoint": endpoint, "token_source": resolved.source,
            "cached": cached, "identity": me,
        }))
        return

    extra = [f"  token:    {auth.redact(resolved.token)} (from {resolved.source})"]
    if cached:
        extra.append("  note:     server unreachable — showing the identity cached at last login")
    for line in _identity_lines(me, endpoint=endpoint, profile=profile, extra=extra):
        click.echo(line)


@cli.command()
@click.option("--profile", "profile_opt", default=None, help="Credential profile to log out of.")
@click.option("--json", "json_output", is_flag=True, help="Emit machine-readable JSON instead of human-readable text.")
@click.pass_context
def logout(ctx: click.Context, profile_opt: str | None, json_output: bool) -> None:
    """Remove the stored credential for the active profile.

    Only touches this profile, and cannot revoke the token itself — revoke it in
    the web app if it may have leaked.
    """
    import os

    from vcc import auth, config

    as_json = bool(ctx.obj.get("json")) or json_output
    profile = config.resolve_profile(profile_opt or ctx.obj.get("profile"))

    cleared = auth.delete_token(profile)
    state_cleared = auth.clear_profile_state(profile)

    if as_json:
        click.echo(json.dumps({"ok": True, "profile": profile, "cleared": cleared, "state_cleared": state_cleared}))
        return

    if cleared or state_cleared:
        where = ", ".join(cleared) if cleared else "local state"
        click.echo(f"✓ logged out of profile '{profile}' (cleared: {where})")
    else:
        click.echo(f"Nothing stored for profile '{profile}' — already logged out.")
    if os.environ.get("VCC_TOKEN"):
        click.echo("  note: VCC_TOKEN is still set in this environment and will keep being used.")


def _submit_reporter(as_json: bool) -> "object":
    """Build an on_event callback that renders progress (quiet for --json).

    Upload progress goes through ProgressRenderer, which shows a bar, live
    transfer rate, and ETA on a TTY, and periodic plain lines when piped.
    """
    import sys

    from vcc.progress import ProgressRenderer, format_bytes

    state: dict[str, object] = {"renderer": None}

    def report(kind: str, **data: object) -> None:
        if as_json:
            return
        match kind:
            case "prep_start":
                click.echo(f"→ prepping {data['input']} …")
            case "prep_done":
                click.echo(f"  prepped: {data['output']} ({data['normalization']})")
            case "limit_check":
                click.echo("→ checking your team's daily submission allowance …")
            case "create_start":
                click.echo(f"→ creating submission '{data['model_name']}' …")
            case "created":
                click.echo(f"  entry: {data['entry_id']}")
                if data.get("is_final"):
                    click.echo("  ⚠ FINAL WEEK MODE — this submission counts toward final scoring")
            case "resume":
                click.echo(f"→ resuming entry {data['entry_id']} ({data['file']})")
            case "upload_start":
                click.echo("→ uploading …")
            case "upload_progress":
                done, total = int(data["done"]), int(data["total"])  # type: ignore[arg-type]
                renderer = state.get("renderer")
                if renderer is None:
                    renderer = ProgressRenderer(
                        total, stream=sys.stdout, is_tty=sys.stdout.isatty()
                    )
                    state["renderer"] = renderer
                renderer.update(done)  # type: ignore[union-attr]
            case "upload_done":
                renderer = state.get("renderer")
                if renderer is not None:
                    renderer.finish()  # type: ignore[union-attr]
                    state["renderer"] = None
                else:
                    click.echo(f"  uploaded {format_bytes(float(data['bytes']))}")
                if not data.get("verified"):
                    click.echo("  note: storage did not report a checksum for this upload")
            case "launched":
                click.echo(f"→ scoring started (job: {data.get('job_name') or 'n/a'})")
            case "status":
                click.echo(f"  status: {data.get('status')}")
            case "wait_timeout":
                click.echo(f"  still {data.get('status')} — stopped waiting (not a failure)")

    return report


@cli.command()
@click.argument("file", metavar="FILE", required=False, type=click.Path(dir_okay=False))
@click.option("-m", "--model-name", default=None, help="Name for this model on the leaderboard (required).")
@click.option("-d", "--description", default=None, help="Optional description (max 2000 chars).")
@click.option("-g", "--genes", type=click.Path(), default=None, help="Gene list, if FILE is a raw .h5ad that needs prepping.")
@click.option("--perts", type=click.Path(), default=None, help="pert_counts.csv, if FILE is a raw .h5ad — the official list prep checks targets against (required by default when prepping; see --no-verify-targets).")
@click.option("--verify-targets/--no-verify-targets", default=True, show_default=True, help="When prepping a raw .h5ad, check each context predicts exactly its official perturbations. Needs --perts.")
@click.option("--check-cell-counts/--no-check-cell-counts", default=True, show_default=True, help="When prepping a raw .h5ad, require each perturbation to have exactly the official number of cells (400).")
@click.option("--wait", is_flag=True, help="Block until scoring reaches a terminal state.")
@click.option("--poll-interval", type=float, default=5.0, show_default=True, help="Seconds between status polls with --wait.")
@click.option("--wait-timeout", type=float, default=None, help="Give up waiting after N seconds (the submission keeps running).")
# `default` must stay OMITTED. Click >=8.3 decides whether an option can be used bare from
# `self.default is UNSET` (core.py: `_flag_needs_value = self.default is UNSET`), so passing
# `default=None` makes this a value-REQUIRED option: bare `--resume` exits 2 and
# `--resume --json` swallows the next flag. Click 8.1/8.2 keyed off `flag_value is not None`,
# which is why this broke on upgrade rather than on any change of ours.
@click.option("--resume", "resume_id", is_flag=False, flag_value="__only__", help="Resume an interrupted upload (optionally pass its entry id).")
@click.option("--skip-limit-check", is_flag=True, help="Skip the daily-allowance pre-check.")
@click.option("-f", "--force", is_flag=True, help="Overwrite an existing prep output.")
@click.option("--endpoint", "endpoint_opt", default=None, help="Base URL to submit to.")
@click.option("--profile", "profile_opt", default=None, help="Credential profile to use.")
@click.option("--json", "json_output", is_flag=True, help="Emit machine-readable JSON instead of human-readable text.")
@click.pass_context
def submit(
    ctx: click.Context,
    file: str | None,
    model_name: str | None,
    description: str | None,
    genes: str | None,
    perts: str | None,
    verify_targets: bool,
    check_cell_counts: bool,
    wait: bool,
    poll_interval: float,
    wait_timeout: float | None,
    resume_id: str | None,
    skip_limit_check: bool,
    force: bool,
    endpoint_opt: str | None,
    profile_opt: str | None,
    json_output: bool,
) -> None:
    """Upload a prediction and start scoring.

    FILE may be a .vcc (validated and uploaded as-is) or a raw .h5ad, which is
    prepped first — pass -g/--genes and --perts (or --no-verify-targets to skip
    the perturbation check).
    """
    from vcc import api, auth, submit as submit_mod

    as_json = bool(ctx.obj.get("json")) or json_output
    profile, endpoint, _ = _auth_context(ctx, endpoint_opt, profile_opt)

    try:
        resolved = auth.resolve_token(profile)
    except auth.AuthError as exc:
        _fail(ctx, str(exc), as_json, code="not_logged_in")

    resume_data = None
    if resume_id:
        wanted = None if resume_id == "__only__" else resume_id
        resume_data = auth.get_pending_upload(profile, wanted)
        if not resume_data:
            pending = auth.list_pending_uploads(profile)
            hint = (
                f" Pending: {', '.join(pending)}" if pending else " There are no interrupted uploads to resume."
            )
            _fail(ctx, f"Nothing to resume for this profile.{hint}", as_json, code="no_resume")
    else:
        if not file:
            raise click.UsageError("Missing FILE. Usage: vcc submit PRED.vcc -m \"my model\"")
        if not model_name:
            raise click.UsageError("Missing -m/--model-name (required, shown on the leaderboard).")
        if description and len(description) > 2000:
            raise click.UsageError("--description is limited to 2000 characters.")

    # Single-flight: two concurrent `vcc submit` runs would both pre-check, then
    # both try to create an entry — the server rejects the second with a 409, but
    # only after the loser has already prepped and possibly uploaded.
    from vcc.config import config_dir
    from vcc.lock import LockHeldError, SubmitLock

    lock = SubmitLock(config_dir() / "locks" / f"submit-{profile}.lock")
    try:
        lock.acquire()
    except LockHeldError as exc:
        _fail(ctx, str(exc), as_json, code="submit_in_progress")

    try:
        result = submit_mod.run_submit(
            endpoint=endpoint,
            token=resolved.token,
            path=file or "",
            model_name=model_name or "",
            description=description,
            genes=genes,
            perts=perts,
            verify_targets=verify_targets,
            check_cell_counts=check_cell_counts,
            wait=wait,
            poll_interval=poll_interval,
            wait_timeout=wait_timeout,
            on_event=_submit_reporter(as_json),
            force=force,
            skip_limit_check=skip_limit_check,
            resume=resume_data,
            pending_uploads=None if resume_data else auth.list_pending_uploads(profile),
            save_resume=lambda eid, data: auth.save_pending_upload(profile, eid, data),
            clear_resume=lambda eid: auth.clear_pending_upload(profile, eid),
        )
    except (submit_mod.SubmitError, api.ApiError) as exc:
        _fail(ctx, str(exc), as_json, code=getattr(exc, "code", None))
    finally:
        lock.release()

    failed = result.final_status == "failed"

    if as_json:
        click.echo(json.dumps(result.to_dict()))
        if failed:
            ctx.exit(1)  # a failed scoring run must not read as success to a script
        return

    if failed:
        # Upload succeeded but scoring failed — do NOT print ✓ or exit 0.
        click.echo(f"✗ submission failed — entry {result.entry_id}")
        click.echo(f"  final status: {result.final_status}")
        if not _echo_error_info(result.error_info, width=14):  # aligns with "final status: "
            click.echo(f"  (no error detail returned; run: vcc status {result.entry_id})")
        ctx.exit(1)

    click.echo(f"✓ submitted — entry {result.entry_id}")
    if result.final_status:
        click.echo(f"  final status: {result.final_status}")
        if result.final_status == "superseded":
            # Scored fine, but a newer submission of yours holds the team's single
            # board row, so this entry is off the leaderboard (the server keeps only
            # the newest per team). Say so — otherwise `superseded` reads as a bare,
            # unexplained status line under a ✓.
            click.echo(
                "  note: superseded — a newer submission of yours holds your team's "
                "leaderboard spot, so this entry is off the board"
            )
        _echo_scores(result.scores)  # print any scores the entry carries (no-op if none)
    else:
        click.echo(f"  track it with: vcc status {result.entry_id} --wait")


@cli.command()
@click.argument("entry_id")
@click.option("--wait", is_flag=True, help="Block until the submission reaches a terminal state.")
@click.option("--poll-interval", type=float, default=5.0, show_default=True, help="Seconds between polls with --wait.")
@click.option("--wait-timeout", type=float, default=None, help="Give up waiting after N seconds.")
@click.option("--endpoint", "endpoint_opt", default=None, help="Base URL to query.")
@click.option("--profile", "profile_opt", default=None, help="Credential profile to use.")
@click.option("--json", "json_output", is_flag=True, help="Emit machine-readable JSON instead of human-readable text.")
@click.pass_context
def status(
    ctx: click.Context,
    entry_id: str,
    wait: bool,
    poll_interval: float,
    wait_timeout: float | None,
    endpoint_opt: str | None,
    profile_opt: str | None,
    json_output: bool,
) -> None:
    """Show the status (and scores, once published) of one submission."""
    from vcc import api, auth, submit as submit_mod

    as_json = bool(ctx.obj.get("json")) or json_output
    profile, endpoint, _ = _auth_context(ctx, endpoint_opt, profile_opt)

    try:
        resolved = auth.resolve_token(profile)
    except auth.AuthError as exc:
        _fail(ctx, str(exc), as_json, code="not_logged_in")

    try:
        if wait:
            entry = submit_mod.poll_until_terminal(
                endpoint,
                resolved.token,
                entry_id,
                interval=poll_interval,
                timeout=wait_timeout,
                on_event=_submit_reporter(as_json),
            )
        else:
            entry = api.get_submission(endpoint, resolved.token, entry_id)
    except api.ApiError as exc:
        _fail(ctx, str(exc), as_json, code=exc.code)

    # Exit-code contract, computed before the JSON branch returns (scripts consume
    # --json). A failed submission is an error state. So is a response with no
    # status field: that isn't a real submission (a wrong id, or a non-entry body),
    # and printing "status: unknown" with exit 0 let `vcc status "$id" && …` read a
    # non-entry as success (#401).
    status_val = entry.get("status")
    has_status = isinstance(status_val, str) and status_val != ""
    failed = status_val == "failed"
    error_exit = failed or not has_status
    if as_json:
        # Give scripts a machine-readable terminal bit (#416). `is_final` is the
        # final-week board flag (server-set at creation), NOT a done signal, so
        # polling on it never terminates on a normal published run. `is_terminal`
        # uses the same terminal set the CLI's own --wait relies on (submit.is_done
        # over {published, failed, hidden_admin}). `is_final` is left untouched.
        payload = dict(entry)
        # Terminal = "stop polling": a known-done status, OR a non-entry response
        # (no status) that will never resolve — so a `poll-until is_terminal==true`
        # loop halts on a wrong/deleted id instead of spinning forever. The command
        # still exits 1 for that case, so a loop that also checks the exit code sees
        # the error. (Follow-up to #416 — without the `not has_status` arm the poll
        # hang just moved from is_final to is_terminal.)
        payload["is_terminal"] = submit_mod.is_done(status_val) or not has_status
        click.echo(json.dumps(payload))
        if error_exit:
            ctx.exit(1)
        return

    click.echo(f"  entry:    {entry.get('entry_id', entry_id)}")
    click.echo(f"  model:    {entry.get('model_name') or '(unnamed)'}")
    click.echo(f"  status:   {status_val or 'unknown'}")
    if entry.get("is_final"):
        click.echo("  mode:     FINAL (counts toward final scoring)")
    if entry.get("submission_date"):
        click.echo(f"  submitted:{entry['submission_date']}")
    _echo_scores(entry)
    # Render the failure reason readably (the raw dict is still in --json above).
    _echo_error_info(entry.get("error_info"))

    if not has_status:
        click.echo(
            f"vcc status: no submission status returned for '{entry_id}' — it may not be a "
            "valid submission id for your account.",
            err=True,
        )
    if error_exit:
        ctx.exit(1)  # failed, or not a real submission — surface it to scripts


@cli.command()
@click.argument("entry_id", required=False)
@click.option("-y", "--yes", "assume_yes", is_flag=True, help="Do not prompt for confirmation.")
@click.option("--endpoint", "endpoint_opt", default=None, help="Base URL to query.")
@click.option("--profile", "profile_opt", default=None, help="Credential profile to use.")
@click.option("--json", "json_output", is_flag=True, help="Emit machine-readable JSON instead of human-readable text.")
@click.pass_context
def cancel(
    ctx: click.Context,
    entry_id: str | None,
    assume_yes: bool,
    endpoint_opt: str | None,
    profile_opt: str | None,
    json_output: bool,
) -> None:
    """Abandon an in-progress submission, freeing your team's slot.

    Use this when an upload was interrupted or you started submitting the wrong
    file: your team allows one submission in progress at a time, so a stuck upload
    otherwise blocks the next `vcc submit` until it either finishes or ages out.

    Cancelling marks the entry failed and clears the interrupted upload so a fresh
    `vcc submit` works right away. **It does NOT count against your daily limit** —
    only a successfully scored submission does — so abandoning a wrong file is free.

    ENTRY_ID is optional when there is exactly one interrupted upload for this
    profile; pass it explicitly to disambiguate, or to cancel an entry started on
    another machine.

    An UPLOADING submission is always cancellable. One that has moved on to
    `launching`/`scoring` can be cancelled only while its scoring job is still
    waiting in the queue for a machine — once the job actually starts running it
    can't be stopped, and `vcc cancel` will tell you to wait for it.
    """
    from vcc import api, auth, submit as submit_mod
    from vcc.config import config_dir
    from vcc.lock import LockHeldError, SubmitLock

    as_json = bool(ctx.obj.get("json")) or json_output
    profile, endpoint, _ = _auth_context(ctx, endpoint_opt, profile_opt)

    try:
        resolved = auth.resolve_token(profile)
    except auth.AuthError as exc:
        _fail(ctx, str(exc), as_json, code="not_logged_in")

    # Resolve which entry to cancel: the explicit id, or the sole interrupted upload
    # recorded locally. `--resume` uses the same rule (get_pending_upload), so the two
    # stay symmetric — whatever `--resume` would continue is what a bare `cancel` drops.
    target = entry_id
    if not target:
        pending = auth.list_pending_uploads(profile)
        if not pending:
            _fail(
                ctx,
                "Nothing to cancel: no interrupted upload is recorded for this profile. "
                "Pass an entry id to cancel a specific submission (see `vcc status <id>`).",
                as_json,
                code="no_pending",
            )
        elif len(pending) == 1:
            (target,) = pending
        else:
            _fail(
                ctx,
                "More than one interrupted upload is recorded; pass the entry id to cancel. "
                f"Pending: {', '.join(pending)}",
                as_json,
                code="ambiguous",
            )

    # Serialize with `vcc submit` on this machine (the SAME single-flight lock). Without
    # it, cancelling an entry a live `vcc submit` is mid-upload of would race the
    # uploader: we flip it to `failed`, the uploader then finishes and re-sets it to
    # `launching`, silently overriding the cancel. Sharing submit's lock makes one wait
    # for the other instead.
    lock = SubmitLock(
        config_dir() / "locks" / f"submit-{profile}.lock",
        label="vcc cancel",
        advice=(
            "A `vcc submit` is running on this machine. To abort that upload, stop it "
            "(Ctrl-C) — the entry stays cancellable afterwards. Otherwise wait for it to finish."
        ),
    )
    try:
        lock.acquire()
    except LockHeldError as exc:
        _fail(ctx, str(exc), as_json, code="submit_in_progress")

    try:
        # Check the server's view before doing anything: only a still-in-progress entry
        # can be cancelled, and only the states we can cancel WITHOUT racing a live job.
        try:
            entry = api.get_submission(endpoint, resolved.token, target)
        except api.ApiError as exc:
            # Gate on the datastore's own `not_found` code, NOT a bare status 404: a
            # server with no cancel/lookup route returns a code-less 404 whose message
            # says exactly that, and swallowing it as "gone, slot free" would wrongly
            # destroy the resume record on a CLI newer than the deployed frontend.
            if exc.code == "not_found":
                # The lookup is owner-scoped, so a not_found means EITHER our own entry
                # is gone OR the id isn't ours. Distinguish by whether WE recorded it as
                # an interrupted upload: only then is it safe to say the slot is free and
                # clear the record — otherwise it may be a teammate's entry, and claiming
                # the slot is free would be a lie.
                if auth.get_pending_upload(profile, target):
                    auth.clear_pending_upload(profile, target)
                    message = (
                        f"Submission {target} no longer exists, so there is nothing to cancel — "
                        "your team's slot is already free."
                    )
                    if as_json:
                        click.echo(json.dumps({"entry_id": target, "status": "gone", "message": message}))
                    else:
                        click.echo(message)
                    return
                _fail(
                    ctx,
                    f"No in-progress submission of yours with id {target}. It may already be "
                    "finished, or belong to a teammate — ask them to cancel it, or wait for it to "
                    "time out.",
                    as_json,
                    code="not_found",
                )
            _fail(ctx, str(exc), as_json, code=exc.code)

        status_val = entry.get("status")
        if not submit_mod.is_in_progress(status_val):
            # Terminal (published/failed/hidden_admin) or unrecognised: not holding a
            # slot, so there's nothing to free. Clear stale local bookkeeping if done.
            if submit_mod.is_done(status_val):
                auth.clear_pending_upload(profile, target)
            _fail(
                ctx,
                f"Submission {target} has status '{status_val or 'unknown'}', which is not an "
                "in-progress submission — there is nothing to cancel.",
                as_json,
                code="not_cancellable",
            )

        # Confirm before the attempt (human mode only; --json / --yes are
        # non-interactive by contract).
        if not as_json and not assume_yes:
            click.echo(f"This will cancel submission {target} (status: {status_val}) and free your team's slot.")
            click.echo("It does NOT count against your daily limit.")
            # Read the answer with input() rather than click.confirm: on EOF (no answer
            # piped, non-interactive shell) click.confirm's behaviour SPLITS by version —
            # >=8.2 raise Abort, but 8.1.x silently return the default — so the
            # actionable-hint branch never fired on Click 8.1 (which pyproject still
            # declares as the floor, `click>=8.1`, and CI pins in the click-matrix job).
            # input() raises EOFError on EOF on every version, keeping the three cases
            # distinct: a piped y/n is honoured, and a true no-answer gets the --yes hint
            # instead of a bare "Aborted!". KeyboardInterrupt is re-raised as Abort so
            # ^C at the prompt still prints "Aborted!" via main()'s handler.
            click.echo("Cancel it? [y/N]: ", nl=False)
            try:
                answer = input()
                # Anything that isn't an explicit yes declines — fail-safe for a
                # destructive action. (Kept inside the try so `answer` can't be seen
                # as possibly-unbound; _fail always exits.)
                if answer.strip().lower() not in ("y", "yes"):
                    _fail(ctx, "Left the submission alone.", as_json, code="aborted")
            except EOFError:
                _fail(
                    ctx,
                    f"No confirmation received for cancelling {target} — re-run with --yes to skip "
                    "the prompt (or answer interactively).",
                    as_json,
                    code="needs_confirmation",
                )
            except KeyboardInterrupt:
                raise click.Abort()

        # The server owns the decision, because only it can see the Batch job's phase:
        # it just fails an uploading entry, and for a launching/scoring one it deletes
        # the scoring job ONLY while it is still queued (no machine yet), otherwise
        # leaving it alone and reporting `not_cancelled`.
        try:
            result = api.cancel_submission(endpoint, resolved.token, target)
        except api.ApiError as exc:
            # Gate on the datastore `not_found` code, not a bare 404 (a frontend without
            # the cancel route returns a code-less 404 — that must surface, not be read
            # as "gone", which would destroy the resume record). We already passed the
            # owner+in-progress pre-check, so a real not_found here means it vanished
            # mid-cancel — genuinely gone, slot free.
            if exc.code == "not_found":
                auth.clear_pending_upload(profile, target)
                message = (
                    f"Submission {target} no longer exists, so there is nothing to cancel — "
                    "your team's slot is already free."
                )
                if as_json:
                    click.echo(json.dumps({"entry_id": target, "status": "gone", "message": message}))
                else:
                    click.echo(message)
                return
            _fail(ctx, f"Could not cancel {target}: {exc}", as_json, code=exc.code)

        if result.get("status") != "cancelled":
            # Not cancelled: the scoring job is no longer queued. `reason` is the job's
            # actual Batch state, so the message can be accurate rather than always
            # claiming it's still running.
            reason = str(result.get("reason") or "").upper()
            if reason == "TERMINAL":
                # Raced to terminal (published/failed) between the pre-check and now:
                # it isn't holding a slot, so drop the stale local record too.
                auth.clear_pending_upload(profile, target)
                _fail(
                    ctx,
                    f"Submission {target} is no longer in progress (it finished or is already "
                    "terminal), so there is nothing to cancel.",
                    as_json,
                    code="not_cancellable",
                )
            if reason == "NOT_FOUND":
                # The scoring job isn't visible yet — only returned for a just-launched
                # entry (createJob consistency lag of a few seconds). An older entry with
                # no job is freed server-side, so this never means a genuinely stuck one.
                _fail(
                    ctx,
                    f"Submission {target}'s scoring job isn't visible yet — if you just launched "
                    f"it, wait a few seconds and try `vcc cancel {target}` again.",
                    as_json,
                    code="job_not_visible",
                )
            if reason == "RUNNING":
                _fail(
                    ctx,
                    f"Submission {target} has already started scoring, so it can't be cancelled — "
                    f"a running scoring job can't be stopped. Wait for it: vcc status {target} --wait",
                    as_json,
                    code="scoring_in_progress",
                )
            if reason == "SUCCEEDED":
                _fail(
                    ctx,
                    f"Submission {target} has already finished scoring, so there is nothing to cancel. "
                    f"See its result: vcc status {target}",
                    as_json,
                    code="already_scored",
                )
            # FAILED / CANCELLED / DELETION_IN_PROGRESS / terminal / unknown — the job is
            # no longer queued and no longer freeable here; a stuck one clears on its own.
            _fail(
                ctx,
                f"Submission {target} can't be cancelled — its scoring job is no longer queued (it "
                f"may already be running or finished). If it's stuck it will clear on its own shortly; "
                f"check it: vcc status {target} --wait",
                as_json,
                code="not_cancellable",
            )

        auth.clear_pending_upload(profile, target)
        killed_job = bool(result.get("killed_job"))
        job_delete_failed = bool(result.get("job_delete_failed"))
    finally:
        lock.release()

    if as_json:
        click.echo(json.dumps({
            "entry_id": target, "status": "cancelled",
            "killed_job": killed_job, "job_delete_failed": job_delete_failed,
        }))
        return
    click.echo(f"✓ cancelled — entry {target}")
    if killed_job:
        click.echo("  stopped the queued scoring job before it started running.")
    if job_delete_failed:
        # The entry is freed, but the queued job couldn't be deleted and may still run.
        # If it finishes scoring it will publish and count — so this is NOT a clean stop.
        click.echo(f"  ⚠ its scoring job could not be stopped and may still run — check `vcc status {target}`.")
        click.echo("    if it finishes scoring it will count against your daily limit.")
    click.echo("  your team's submission slot is free; run `vcc submit` when ready.")


@cli.group()
def datasets() -> None:
    """List and download Virtual Cell Challenge reference data."""


@datasets.command("list")
@click.option("--endpoint", "endpoint_opt", default=None, help="Base URL to query.")
@click.option("--profile", "profile_opt", default=None, help="Credential profile to use.")
@click.option("--json", "json_output", is_flag=True, help="Emit machine-readable JSON instead of human-readable text.")
@click.pass_context
def datasets_list(
    ctx: click.Context, endpoint_opt: str | None, profile_opt: str | None, json_output: bool
) -> None:
    """Show which datasets you can download."""
    from vcc import auth, datasets as ds

    as_json = bool(ctx.obj.get("json")) or json_output
    profile, endpoint, _ = _auth_context(ctx, endpoint_opt, profile_opt)

    try:
        resolved = auth.resolve_token(profile)
    except auth.AuthError as exc:
        _fail(ctx, str(exc), as_json, code="not_logged_in")

    try:
        catalog = ds.list_datasets(endpoint, resolved.token)
    except ds.DatasetError as exc:
        _fail(ctx, str(exc), as_json)

    if as_json:
        click.echo(json.dumps({"datasets": catalog}))
        return

    if not catalog:
        click.echo("No datasets are available.")
        return
    width = max(len(str(d.get("id", ""))) for d in catalog)
    for item in catalog:
        mark = "✓" if item.get("available") else "·"
        line = f"  {mark} {str(item.get('id','')):<{width}}  {item.get('filename','')}"
        click.echo(line)
        if item.get("description"):
            click.echo(f"      {item['description']}")
        if not item.get("available"):
            reason = item.get("unavailable_reason") or "unavailable"
            pretty = "only available during the final week" if reason == "final_week_not_active" else reason
            click.echo(f"      unavailable — {pretty}")
    click.echo("\nDownload with: vcc datasets download <id>")


@datasets.command("download")
@click.argument("dataset_id")
@click.option("-o", "--output", type=click.Path(file_okay=True, dir_okay=False), default=None, help="Write to this exact path instead of <dir>/<filename>.")
@click.option("-d", "--dir", "dest_dir", type=click.Path(file_okay=False, dir_okay=True), default=None, help="Directory to download into [default: $VCC_DATA_DIR or cwd].")
@click.option("-f", "--force", is_flag=True, help="Re-download even if the file is already present and verified.")
@click.option("--endpoint", "endpoint_opt", default=None, help="Base URL to query.")
@click.option("--profile", "profile_opt", default=None, help="Credential profile to use.")
@click.option("--json", "json_output", is_flag=True, help="Emit machine-readable JSON instead of human-readable text.")
@click.pass_context
def datasets_download(
    ctx: click.Context,
    dataset_id: str,
    output: str | None,
    dest_dir: str | None,
    force: bool,
    endpoint_opt: str | None,
    profile_opt: str | None,
    json_output: bool,
) -> None:
    """Download a dataset by id (see `vcc datasets list`).

    Resumes an interrupted download, re-mints the link if it expires mid-transfer,
    and verifies the finished file against the checksum the server advertises.
    """
    import sys

    from vcc import auth, datasets as ds
    from vcc.progress import ProgressRenderer, format_bytes

    as_json = bool(ctx.obj.get("json")) or json_output
    profile, endpoint, _ = _auth_context(ctx, endpoint_opt, profile_opt)

    try:
        resolved = auth.resolve_token(profile)
    except auth.AuthError as exc:
        _fail(ctx, str(exc), as_json, code="not_logged_in")

    renderer: ProgressRenderer | None = None

    def report(kind: str, **data: object) -> None:
        if as_json:
            return
        match kind:
            case "verify_existing":
                click.echo(f"→ found an existing file — verifying {data['path']} …")
            case "existing_corrupt":
                click.echo("  existing file failed verification — downloading again")
            case "resume":
                click.echo(f"→ resuming a partial download ({format_bytes(float(data['bytes']))} already on disk)")
            case "download_start":
                size = data.get("size_bytes")
                pretty = format_bytes(float(size)) if size else "unknown size"
                click.echo(f"→ downloading {data['filename']} ({pretty}) → {data['path']}")
            case "url_refresh":
                click.echo("  download link expired — fetching a fresh one and continuing")

    def on_progress(done: int, total: int) -> None:
        nonlocal renderer
        if as_json:
            return
        if renderer is None:
            # download_file reports the starting offset first, so `done` here is
            # where this run actually began — 0 fresh, >0 on a resume.
            renderer = ProgressRenderer(
                total, stream=sys.stdout, is_tty=sys.stdout.isatty(),
                verb="downloaded", initial=done,
            )
        renderer.update(done)

    try:
        outcome = ds.download_dataset(
            endpoint,
            resolved.token,
            dataset_id,
            dest_dir=dest_dir,
            output=output,
            force=force,
            on_event=report,
            progress=on_progress,
        )
    except ds.DatasetError as exc:
        if renderer is not None:
            click.echo("")
        _fail(ctx, str(exc), as_json)

    if renderer is not None:
        renderer.finish()

    if as_json:
        click.echo(json.dumps(outcome.to_dict()))
        return

    if outcome.skipped:
        click.echo(f"✓ {outcome.filename} already downloaded — {outcome.path}")
    else:
        click.echo(f"✓ downloaded {outcome.filename} → {outcome.path}")
    if outcome.checksum_ok:
        click.echo(f"  verified: {outcome.verified_with} checksum matches")
    elif outcome.checksum_ok is None:
        click.echo("  verified: not verified (no checksum available from the server)")
    for note in outcome.notes:
        click.echo(f"  note: {note}")


@cli.group()
def skill() -> None:
    """Install the VCC agent skill into your coding agent (Claude Code / Codex / Gemini)."""


@skill.command("install")
@click.option(
    "--agent",
    type=click.Choice(["auto", "claude", "codex", "gemini", "all"]),
    default="auto",
    show_default=True,
    help="Which agent(s) to install into. 'auto' = every agent already present on "
    "the machine (falls back to claude if none); 'all' = all three regardless.",
)
@click.option("--dir", "dir_", type=click.Path(), default=None, help="Install into this exact directory instead of the per-agent default.")
@click.option("--force", is_flag=True, help="Overwrite a target directory vcc didn't create.")
@click.option("--json", "json_output", is_flag=True, help="Emit machine-readable JSON instead of human-readable text.")
@click.pass_context
def skill_install_cmd(ctx: click.Context, agent: str, dir_: str | None, force: bool, json_output: bool) -> None:
    """Copy the bundled skill into your agent's skills directory.

    The skill ships inside the CLI but agents don't read skills from Python
    packages, so this copies it where the agent looks. Restart your agent
    session (or /reload) afterward so it picks up the new skill.
    """
    from vcc import skill_install

    as_json = bool((ctx.obj or {}).get("json")) or json_output
    try:
        results = skill_install.install(agent=agent, dir_=dir_, force=force)
    except skill_install.SkillInstallError as exc:
        _fail(ctx, str(exc), as_json)
        return  # unreachable — _fail exits — but keeps type-checkers happy

    failed = [r for r in results if r.status == "error"]
    if as_json:
        click.echo(json.dumps({"installed": [r.to_dict() for r in results]}))
        if failed:
            ctx.exit(1)
        return
    for r in results:
        if r.status == "error":
            click.echo(f"vcc: {r.path}: {r.error}", err=True)
        else:
            click.echo(f"✓ vcc skill {r.status} → {r.path}")
    if not failed:
        click.echo("  Restart your agent session (or run /reload) so it picks up the skill.")
        # In auto mode we install for whatever agents are already present; if that was
        # just the Claude fallback, point at the flag for a not-yet-installed agent.
        if agent == "auto" and [r.agent for r in results] == ["claude"]:
            click.echo("  (another agent? install it first, then re-run — or force now with --agent codex|gemini|all)")
    if failed:
        ctx.exit(1)


@skill.command("uninstall")
@click.option(
    "--agent",
    type=click.Choice(["auto", "claude", "codex", "gemini", "all"]),
    default="auto",
    show_default=True,
    help="Which agent(s) to remove from. 'auto' = every agent present on the machine.",
)
@click.option("--dir", "dir_", type=click.Path(), default=None, help="Remove from this exact directory instead of the per-agent default.")
@click.option("--json", "json_output", is_flag=True, help="Emit machine-readable JSON instead of human-readable text.")
@click.pass_context
def skill_uninstall_cmd(ctx: click.Context, agent: str, dir_: str | None, json_output: bool) -> None:
    """Remove a skill directory previously installed by vcc (leaves foreign dirs untouched)."""
    from vcc import skill_install

    as_json = bool((ctx.obj or {}).get("json")) or json_output
    try:
        results = skill_install.uninstall(agent=agent, dir_=dir_)
    except skill_install.SkillInstallError as exc:
        _fail(ctx, str(exc), as_json)
        return  # unreachable — _fail exits — but keeps type-checkers happy

    failed = [r for r in results if r.status == "error"]
    if as_json:
        click.echo(json.dumps({"removed": [r.to_dict() for r in results]}))
        if failed:
            ctx.exit(1)
        return
    if not results:
        click.echo("Nothing to remove — no vcc skill installed there.")
        return
    for r in results:
        if r.status == "error":
            click.echo(f"vcc: {r.path}: {r.error}", err=True)
        else:
            click.echo(f"✓ vcc skill removed → {r.path}")
    if failed:
        ctx.exit(1)


@skill.command("path")
@click.option(
    "--agent",
    type=click.Choice(["claude", "codex", "gemini"]),
    default="claude",
    show_default=True,
    help="Which agent's skills directory to print.",
)
@click.option("--json", "json_output", is_flag=True, help="Emit machine-readable JSON instead of human-readable text.")
@click.pass_context
def skill_path_cmd(ctx: click.Context, agent: str, json_output: bool) -> None:
    """Print where `vcc skill install` would put the skill for an agent (installs nothing)."""
    from vcc import skill_install

    as_json = bool((ctx.obj or {}).get("json")) or json_output
    target = str(skill_install.agent_target(agent))
    if as_json:
        click.echo(json.dumps({"path": target, "agent": agent}))
    else:
        click.echo(target)


def _value_taking_opts() -> frozenset[str]:
    """Every option string in the command tree that consumes the NEXT argv token.

    Derived from Click's own parameter objects rather than hardcoded, so it cannot
    drift as options are added or renamed — a stale hand-maintained list would
    silently reintroduce the bug `_json_requested` uses this to avoid.
    """
    opts: set[str] = set()

    def walk(command: click.Command) -> None:
        for param in command.params:
            # is_flag options take no value, so they never swallow the next token.
            if isinstance(param, click.Option) and not param.is_flag:
                opts.update(param.opts)
                opts.update(param.secondary_opts)
        for sub in getattr(command, "commands", {}).values():
            walk(sub)

    walk(cli)
    return frozenset(opts)


def _json_requested(argv: list[str]) -> bool:
    """Did the user ask for JSON output?

    Read from argv rather than the Click context because a *usage* error can
    happen before `--json` is parsed. The context is NOT a usable substitute: when
    an unknown flag kills the parse, `ctx.params` never records a `--json` that
    was genuinely passed, and answering "no" there would re-break the contract
    #382 fixed (a script asking for JSON getting plain text back).

    Two things stop a bare token scan from over-matching:

    - anything after a ``--`` separator is an operand, not a flag;
    - a ``--json`` that is the VALUE of a value-taking option is not a request for
      JSON. `vcc submit -m --json` names a model ``--json``; it used to emit JSON
      usage errors the user never asked for.

    Erring toward True is deliberate on anything still ambiguous: emitting JSON
    when it wasn't wanted is cosmetic, while emitting text when it was breaks
    machine consumers.
    """
    value_taking = _value_taking_opts()
    previous: str | None = None
    for arg in argv:
        if arg == "--":
            return False
        if arg == "--json" and previous not in value_taking:
            return True
        previous = arg
    return False


def main() -> None:
    """Console-script entry point (see [project.scripts] in pyproject.toml).

    Click is driven with ``standalone_mode=False`` so a **usage** error (a missing
    or bad flag — Click's own parsing, exit 2) can be rendered as JSON too. In
    standalone mode Click catches UsageError itself and prints its usage text
    before we ever see it, which silently broke the documented `--json` contract
    for an entire class of errors (#382): runtime failures were `{"error": ...}`
    but `vcc sample --json` with no -g emitted plain text.

    With standalone_mode off, Click hands back what it would have exited with, so
    this function owns the exit codes: `ctx.exit(n)` RETURNS n here rather than
    raising SystemExit, and ClickException/Abort propagate instead of printing.
    """
    argv = sys.argv[1:]
    as_json = _json_requested(argv)
    try:
        rv = cli.main(args=argv, standalone_mode=False)
    except click.UsageError as exc:
        if as_json:
            payload: dict[str, object] = {"error": exc.format_message(), "code": "usage_error"}
            click.echo(json.dumps(payload), err=True)
        else:
            # Delegate to Click so the human-readable form stays byte-identical
            # to what it printed before — reimplementing the usage/hint block got
            # the help-option name wrong ('-h' vs '--help').
            exc.show()
        sys.exit(exc.exit_code)
    except click.ClickException as exc:
        if as_json:
            click.echo(json.dumps({"error": exc.format_message()}), err=True)
        else:
            exc.show()
        sys.exit(exc.exit_code)
    except click.Abort:
        click.echo("Aborted!", err=True)
        sys.exit(1)
    except Exception as exc:  # noqa: BLE001 — deliberate last-resort backstop
        # Backstop for the --json / no-traceback contract. Every *expected* failure
        # is raised as a Click / Prep / Submit / Api error and handled above or
        # inside the command, but an unforeseen input can still reach an unguarded
        # call and raise a bare exception (a non-string endpoint in state.json →
        # AttributeError #403; a non-finite n_cells → OverflowError #421; a
        # negative --seed → numpy ValueError #405; a directory *.vcc →
        # IsADirectoryError #402; a control-char endpoint → httpx.InvalidURL #419).
        # Without this, that exception escapes as a raw Python traceback, which both
        # violates the documented --json error shape and dumps an internal stack at
        # the user. Map it to the same shape as every other error; the specific
        # sites are ALSO guarded (clearer messages), this is the safety net.
        import os
        if os.environ.get("VCC_TRACEBACK"):
            import traceback
            traceback.print_exc()
        msg = f"{type(exc).__name__}: {exc}"
        if as_json:
            click.echo(json.dumps({"error": msg, "code": "internal_error"}), err=True)
        else:
            click.echo(f"vcc: unexpected error — {msg}", err=True)
            click.echo("  This is a bug; re-run with VCC_TRACEBACK=1 for the full trace and report it.", err=True)
        sys.exit(1)
    # ctx.exit(n) comes back as an int return value in non-standalone mode.
    sys.exit(rv if isinstance(rv, int) else 0)


if __name__ == "__main__":
    main()
