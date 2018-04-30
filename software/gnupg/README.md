# How-to generate a new GPG key

Ref.: https://help.github.com/articles/generating-a-new-gpg-key/

```
$ gpg --list-secret-keys --keyid-format LONG

gpg: directory '/Users/ali/.gnupg' created
gpg: keybox '/Users/ali/.gnupg/pubring.kbx' created
gpg: /Users/ali/.gnupg/trustdb.gpg: creato il trustdb
```

```
$ gpg --full-generate-key

gpg (GnuPG) 2.2.0; Copyright (C) 2017 Free Software Foundation, Inc.
This is free software: you are free to change and redistribute it.
There is NO WARRANTY, to the extent permitted by law.

Per favore scegli che tipo di chiave vuoi:
   (1) RSA and RSA (default)
   (2) DSA and Elgamal
   (3) DSA (firma solo)
   (4) RSA (firma solo)

> 1
```

```
RSA anahtarlari 1024 bit ile 4096 bit arasinda olmali.
Istediginiz anahtar uzunlugu nedir? (2048)

> 4096
```

```
La dimensione richiesta della chiave `e 4096 bit
Per favore specifica per quanto tempo la chiave sar`a valida.
         0 = la chiave non scadr`a
      <n>  = la chiave scadr`a dopo n giorni
      <n>w = la chiave scadr`a dopo n settimane
      <n>m = la chiave scadr`a dopo n mesi
      <n>y = la chiave scadr`a dopo n anni
Chiave valida per? (0)

> 0
```

```
Anahtar hep gecerli olacak
Bu dogru mu? (e/H ya da y/N)

> y
```

```
GnuPG anahtarinizi betimlemek icin bir kullanici kimligi olusturmaya ihtiyac duyuyor.

Nome e Cognome: Ali Servet Donmez
Indirizzo di Email: ali@balsamiq.com
Commento: Convox

Hai selezionato questo User Id:
    "Ali Servet Donmez (Convox) <ali@balsamiq.com>"

Modifica (N)ome, (C)ommento, (E)mail oppure (O)kay/(Q)uit?

> O
```

```
┌─────────────────────────────────────────────────────────────┐
│ Please enter the passphrase to                              │
│ protect your new key                                        │
│                                                             │
│ Anahtar Parolası: ________________________________________ │
│                                                             │
│        <OK>                                   <Cancel>      │
└─────────────────────────────────────────────────────────────┘

Dobbiamo generare un mucchio di byte casuali. `E una buona idea eseguire
qualche altra azione (scrivere sulla tastiera, muovere il mouse, usare i
dischi) durante la generazione dei numeri primi; questo da al generatore di
numeri casuali migliori possibilit`a di raccogliere abbastanza entropia.
Dobbiamo generare un mucchio di byte casuali. `E una buona idea eseguire
qualche altra azione (scrivere sulla tastiera, muovere il mouse, usare i
dischi) durante la generazione dei numeri primi; questo da al generatore di
numeri casuali migliori possibilit`a di raccogliere abbastanza entropia.
gpg: anahtar 6867755036FD7C4E son derece g"uvenli olarak imlendi.
gpg: directory '/Users/ali/.gnupg/openpgp-revocs.d' created
gpg: revocation certificate stored as '/Users/ali/.gnupg/openpgp-revocs.d/1F45E70AA5FDF1844324B62E6867755036FD7C4E.rev'
chiavi pubbliche e segrete create e firmate.

pub   rsa4096 2017-09-18 [SC]
      1F45E70AA5FDF1844324B62E6867755036FD7C4E
uid                      Ali Servet Donmez (Convox) <ali@balsamiq.com>
sub   rsa4096 2017-09-18 [E]
```

```
$ gpg --list-secret-keys --keyid-format LONG

/Users/ali/.gnupg/pubring.kbx
-----------------------------
sec   rsa4096/6867755036FD7C4E 2017-09-18 [SC]
      1F45E70AA5FDF1844324B62E6867755036FD7C4E
uid                 [   son  derece   ] Ali Servet Donmez (Convox) <ali@balsamiq.com>
ssb   rsa4096/999A9555A5DF5B7D 2017-09-18 [E]
```

```
$ gpg --armor --export 6867755036FD7C4E

-----BEGIN PGP PUBLIC KEY BLOCK-----

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
6WvjquuTg9Xm
=Ulr5
-----END PGP PUBLIC KEY BLOCK-----
```
