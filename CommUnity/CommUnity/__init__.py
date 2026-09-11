# Let Django's MySQL backend run on the pure-Python PyMySQL driver when the
# compiled `mysqlclient` package is not installed (common on Windows).
try:
    import MySQLdb  # noqa: F401
except ImportError:
    try:
        import pymysql

        pymysql.install_as_MySQLdb()
    except ImportError:
        pass
