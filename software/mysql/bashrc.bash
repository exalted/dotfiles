mysql@5.7-start() {
    mysql@8.0-stop
    ( "$HOMEBREW_PREFIX/opt/mysql@5.7/bin/mysqld_safe" --datadir="$HOMEBREW_PREFIX/var/mysql@5.7" > /dev/null 2>&1 & )
}
mysql@5.7-stop() {
    "$HOMEBREW_PREFIX/opt/mysql@5.7/bin/mysqladmin" -u root shutdown > /dev/null 2>&1
}

mysql@8.0-start() {
    mysql@5.7-stop
    ( "$HOMEBREW_PREFIX/opt/mysql@8.0/bin/mysqld_safe" --datadir="$HOMEBREW_PREFIX/var/mysql@8.0" > /dev/null 2>&1 & )
}
mysql@8.0-stop() {
    "$HOMEBREW_PREFIX/opt/mysql@8.0/bin/mysqladmin" -u root shutdown > /dev/null 2>&1
}
