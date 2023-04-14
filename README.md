<h1 align="center"><code>TinyCDN</code></h1>

<div align="center">
    <sub>Created by <a href="https://github.com/jgengo">Jordane Gengo (titus)</a></sub>
</div>
<div align="center">
    <sub>From <a href="https://hive.fi">Hive Helsinki</a></sub>
</div>

## Description

`TinyCDN` is a simple application designed to make it easy to access your 42 students' profile pictures internally.

You may wonder why such an application is necessary. Perhaps you want to create a static website or a simple app without the hassle of setting up a 42API connector or OAuth to retrieve your students' profile picture links. In that case, TinyCDN can help you access any of your students' pictures using the URL tinycdn.domain.nl/LE_LOGIN. This is no longer possible through 42 due to GDPR restrictions on external exposure of student profile pictures.

<br /><br />

## Install

1. Create a new 42API application [here](https://profile.intra.42.fr/oauth/applications)

2. Create the .env file and fill in the required information

```bash
copy .env.sample .env
```

| key       | desc                                       |
| :-------- | :----------------------------------------- |
| CAMPUS_ID | Your campus ID on the intranet             |
| FT_ID     | Your 42API UID starting with `u-s4t2af`    |
| FT_SECRET | Your 42API Secret starting with `s-s4t2af` |

<br />

## Run

```bash
docker-compose up -d --build
```

I would then recommend to take a look at the logs, making sure you don't see any errors.

```bash
docker-compose logs -f
```

**Test**

Open a browser and try to access https://tinycdn.domain.nl/ it should returns the following:

```bash
{
  "name": "TinyCDN",
  "version": "0.0.3"
}
```

If so, try to access a student profile picture via: https://tinycdn.domain.nl/LOGIN. For example, https://tinycdn.domain.nl/jgengo

<br /><br />

## Dev

If you want to run this application in dev mode:

- debug logs
- auto reload on edition
- http only

You can follow the following steps:

1. create a .env.dev file and fill in the required fields.

```
cp .env.sample .env.dev
```

2. Run your container:

```bash
docker-compose -f dc-dev.yml up --build -d
```

3. Read the logs to make sure everything went ok

```bash
docker-compose -f dc-dev.yml logs -f
```

4. Access it via : http://localhost:8000

Feel free to change the port forwarding if you want to use something else than 8000 in the dc-dev.yml

<br /><br />

## Todo

- [ ] Propose to save the image locally.
