import logging

import click

from kit.core.ingestion import FilesIngestionFlow

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(filename)s | %(message)s", level=logging.ERROR)

logger = logging.getLogger("kit")
logger.setLevel(logging.INFO)


def auth_from_cli(app, user, host):
    from kit.helpers import get_azure_cli_auth_token

    if app:
        aad_app_id, app_key = app.split(":")
        return dict(aad_app_id=aad_app_id, app_key=app_key, authority_id="72f988bf-86f1-41af-91ab-2d7cd011db47")
    if user:
        user_id, password = user.split(":")
        return dict(user_id=user_id, password=password, authority_id="72f988bf-86f1-41af-91ab-2d7cd011db47")

    return dict(user_token=get_azure_cli_auth_token(host))


@click.group()
@click.pass_context
def main(ctx):
    pass


@main.command()
@click.option("--user", type=str)
@click.option("--app", type=str)
@click.option("--nowait", is_flag=True, default=False)
@click.option("--queued", "-q", is_flag=True, default=False)
@click.option("--host", "-h", type=str)
@click.option("--files", "-f", type=str)
@click.option("--directory", "-d", type=click.Path())
@click.option("--table", "-t", type=str)
@click.option("--database", "-db", type=str)
@click.option("--pattern", type=str)
@click.option("--headers", is_flag=True, default=False)
@click.pass_context
def ingest(ctx, headers, pattern, database, table, directory, files, host, queued, nowait, app, user):
    from kit.core.ingestion import FolderIngestionFlow

    if directory:
        flow = FolderIngestionFlow(
            directory, host, database, auth=auth_from_cli(app, user, host), queued=queued, no_wait=nowait, pattern=pattern, headers=headers
        )
        flow.run()
    elif files:
        flow = FilesIngestionFlow(
            files.split(','), host, database, target_table=table, auth=auth_from_cli(app, user, host), queued=queued, no_wait=nowait, headers=headers
        )
        flow.run()


@main.command()
@click.option("--table", "-t", type=str)
@click.option("--database", "-db", type=str)
@click.option("--user", type=str)
@click.option("--app", type=str)
@click.option("--host", "-h", type=str)
@click.option("-n", type=str)
@click.pass_context
def top(ctx, n, host, app, user, database, table):
    auth = auth_from_cli(app, user, host)
    from kit.backends.kusto import KustoBackend

    kusto_backend = KustoBackend(host, auth)
    print(kusto_backend.peek_table(database, table, n))


@main.command()
@click.option("--table", "-t", type=str)
@click.option("--database", "-db", type=str)
@click.option("--user", type=str)
@click.option("--app", type=str)
@click.option("--host", "-h", type=str)
@click.pass_context
def count(ctx, host, app, user, database, table):
    auth = auth_from_cli(app, user, host)
    from kit.backends.kusto import KustoBackend

    kusto_backend = KustoBackend(host, auth)
    print(kusto_backend.count_rows(database, table))


@main.group()
@click.pass_context
def schema(ctx):
    pass


@schema.command()
@click.pass_context
@click.option("--user", type=str)
@click.option("--app", type=str)
@click.option("--sql", "-sql", type=str)
@click.option("--host", "-h", type=str)
@click.option("--database", "-db", type=str)
@click.option("--directory", "-d", type=click.Path())
@click.option("--file", "-f", type=click.Path())
def create(ctx, file, directory, database, host, sql, app, user):
    if file:
        # TODO: should resolve file location (can be s3 / azure storage / local file)
        from kit.backends import fs
        from kit.models.database import Database

        table = fs.table_from_file(file)

        db = Database("temp", [table])

    elif directory:
        from kit.backends import fs
        from kit.models.database import Database

        db = fs.database_from_folder(directory)
    elif host:
        auth = auth_from_cli(app, user, host)
        from kit.backends.kusto import KustoBackend

        kusto_backend = KustoBackend(host, auth)
        db = kusto_backend.describe_database(database)
    elif sql:
        import kit.specifications.sql as sql_spec

        db = sql_spec.database_from_sql(sql)
    else:
        raise ValueError("No method was chosen. use `kit schema create --help` ")

    print(db.to_json())


@schema.command()
@click.pass_context
@click.option("--user", type=str)
@click.option("--app", type=str)
@click.option("--host", "-h", type=str)
@click.option("--database", "-db", type=str)
@click.option("--file", "-f", type=click.Path())
def apply(ctx, file, database, host, app, user):
    from kit.models.database import Database
    db = Database.load(file)
    auth = auth_from_cli(app, user, host)
    from kit.backends.kusto import KustoBackend

    kusto_backend = KustoBackend(host, auth)

    # target db
    db.name = database
    kusto_backend.enforce_schema(db)


if __name__ == "__main__":
    main()
