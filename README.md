# Built

A asset management system for construction companies

## Table of Contents

- [Built](#built)
  - [Table of Contents](#table-of-contents)
  - [Installation](#installation)
    - [Fullstack](#fullstack)
    - [Manual](#manual)
      - [Backend](#backend)
      - [Frontend(dev)](#frontenddev)
      - [Frontend(prod)](#frontendprod)

## Installation

### Fullstack

```sh
docker compose up -d
```

### Manual

#### Backend

```sh
cd api
python main.py
```

#### Frontend(dev)

```sh
cd frontend
pnpm run dev
```

#### Frontend(prod)

```sh
cd frontend
pnpm run build
pnpm run start
```
