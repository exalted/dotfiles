#!/System/Library/Frameworks/Ruby.framework/Versions/Current/usr/bin/ruby
require_relative '../../src/helpers'

# `brew install mysql`, at any version, will create `$(brew --prefix)/var/mysql`
# folder. However, when you install multiple versions this becomes a problem.
# Here we're creating separate folders for each version, inspired by how
# `brew formula mysql` does things.
# Together with `mysql@X-start` and `mysql@X-stop` aliases, things work as
# one would expected.

brew 'mysql@5.7'
Kernel.system "rm -rf \"$(brew --prefix)/var/mysql\""
unless File.directory? "#{`brew --prefix`.chomp}/var/mysql@5.7"
  Kernel.system "\"$(brew --prefix)/opt/mysql@5.7/bin/mysqld\" --initialize-insecure --user=ali --basedir=\"$(brew --prefix)/opt/mysql@5.7\" --datadir=\"$(brew --prefix)/var/mysql@5.7\" --tmpdir=/tmp"
end

brew 'mysql@8.0'
Kernel.system "rm -rf \"$(brew --prefix)/var/mysql\""
unless File.directory? "#{`brew --prefix`.chomp}/var/mysql@8.0"
  Kernel.system "\"$(brew --prefix)/opt/mysql@8.0/bin/mysqld\" --initialize-insecure --user=ali --basedir=\"$(brew --prefix)/opt/mysql@8.0\" --datadir=\"$(brew --prefix)/var/mysql@8.0\" --tmpdir=/tmp"

  # TODO: This is possibly buggy, because if a MySQL server is already running this will fail to start:
  Kernel.system "\"$(brew --prefix)/opt/mysql@8.0/bin/mysqld_safe\" --datadir=\"$(brew --prefix)/var/mysql@8.0\" &"
  sleep 5 # MySQL might take a few seconds to start

  Kernel.system "\"$(brew --prefix)/opt/mysql@8.0/bin/mysql\" -u root --execute=\"update mysql.user set plugin = 'mysql_native_password';\""
  Kernel.system "\"$(brew --prefix)/opt/mysql@8.0/bin/mysql\" -u root --execute=\"DROP USER 'mysql.infoschema'@'localhost';\""
  Kernel.system "\"$(brew --prefix)/opt/mysql@8.0/bin/mysql\" -u root --execute=\"CREATE USER 'mysql.infoschema'@'localhost';\""
  Kernel.system "\"$(brew --prefix)/opt/mysql@8.0/bin/mysql\" -u root --execute=\"UPDATE mysql.user SET max_questions = 0, max_updates = 0, max_connections = 0 WHERE User = 'mysql.infoschema' AND Host = 'localhost';\""
  Kernel.system "\"$(brew --prefix)/opt/mysql@8.0/bin/mysql\" -u root --execute=\"GRANT CREATE USER, DELETE, SELECT, EXECUTE, CREATE ROUTINE, ALTER ROUTINE, GRANT OPTION, REFERENCES, CREATE VIEW, TRIGGER, FILE, UPDATE, DROP, CREATE, REPLICATION CLIENT, REPLICATION SLAVE, CREATE TABLESPACE, LOCK TABLES, EVENT, INDEX, ALTER, SHOW VIEW, RELOAD, SHOW DATABASES, INSERT, SHUTDOWN, SUPER, PROCESS, CREATE TEMPORARY TABLES ON *.* TO 'mysql.infoschema'@'localhost';\""
  Kernel.system "\"$(brew --prefix)/opt/mysql@8.0/bin/mysql\" -u root --execute=\"FLUSH PRIVILEGES;\""

  Kernel.system "\"$(brew --prefix)/opt/mysql@8.0/bin/mysqladmin\" -u root shutdown"
end

bash_source_relative
