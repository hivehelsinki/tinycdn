<h1 align="center"><code>TinyCDN</code></h1>

<div align="center">
    <sub>
        Created by <a href="https://github.com/jgengo">Jordane Gengo (titus)</a>,  
        From <a href="https://hive.fi">Hive Helsinki</a>
    </sub>
</div>

# Description
`TinyCDN` is a simple application designed to make it easy to access your 42 students' profile pictures internally.

You may wonder why such an application is necessary. Perhaps you want to create a static website or a simple app without the hassle of setting up a 42API connector or OAuth to retrieve your students' profile picture links. In that case, TinyCDN can help you access any of your students' pictures using the URL tinycdn.domain.nl/LE_LOGIN. This is no longer possible through 42 due to GDPR restrictions on external exposure of student profile pictures.


## Install

1. Create a new 42API application [here](https://profile.intra.42.fr/oauth/applications)

<br />

2. Create the .env file and fill in the required information
```bash
copy .env.sample .env
```

|  Key | Description |
| :---         | :---      |
| CAMPUS_ID    | Your campus ID on the intranet |
| FT_ID     | Your 42API UID starting with `u-s4t2af` |
| FT_SECRET | Your 42API Secret starting with `s-s4t2af` |

<br />

3. You will need to add your SSL certs into `./nginx/ssl` like so:

```
├── nginx.conf
├── nginx.dev.conf
└── ssl
    ├── cert.crt
    ├── cert.key
    └── touch
```

<br />

4. Edit `./nginx/nginx.conf` to suits your need.

In this step you might just need to update the 2 `server_name` lines but also potentially the `allow` ones if you want to only restrict this service to specific internal IPs and `ssl_certificate` lines if you want to use other file names for your certs.

## Run

```bash
docker-compose up -d --build
```

I would then recommend to take a look at the logs, making sure you don't see any errors.

```bash
docker-compose logs -f
```

## Test

Locally testing it works well before setting up your DNS can be done by adding into your /etc/hosts the following line:

```
127.0.0.1 tinycdn.domain.nl
```

Then open a browser and try to access https://tinycdn.domain.nl/ it should returns the following:

```bash
{
  "name": "TinyCDN",
  "version": "0.0.1"
}
```

If so, try to access a student profile picture via: https://tinycdn.domain.nl/LOGIN. For example, https://tinycdn.domain.nl/jgengo