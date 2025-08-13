Mode            Length Hierarchy
----            ------ ---------
d----        175.02 KB Anwill_Service_Notifier_TeleBot
-a---          1.34 KB     ├── .env.example
-a---         81.46 KB     ├── package-lock.json
-a---          1.22 KB     ├── Dockerfile
-a---          1.45 KB     ├── .env
-a---         443.00 B     ├── .dockerignore
-a---         20.81 KB     ├── Makefile
-a---         23.38 KB     ├── README.md
-a---          1.23 KB     ├── CHANGELOG.md
-a---         31.94 KB     ├── .env.lang
-a---           7.00 B     ├── version.txt
-a---         456.00 B     ├── .rsync-exclude
-a---         255.00 B     ├── package.json
-a---         240.00 B     ├── gunicorn.conf.py
-a---          1.38 KB     ├── pyproject.toml
-a---          5.88 KB     ├── run.py
-a---          3.38 KB     ├── .gitignore
-a---         195.00 B     ├── .gitmessage.txt
-a---           0.00 B     ├── __init__.py
d----         15.49 KB     scripts
-a---         859.00 B         ├── notify_telegram.py
-a---         698.00 B         ├── version.py
-a---         856.00 B         ├── add_dep.py
-a---          1.61 KB         ├── generate_changelog_git_changelog.py
-a---         11.22 KB         ├── tree_for_readme.txt
-a---         300.00 B         ├── update_version.py
-a---           0.00 B         ├── __init__.py
d----          8.67 KB         tools
-a---          1.90 KB             ├── gen_tree.py
-a---          3.15 KB             ├── num_code.py
-a---          3.62 KB             ├── dev_secret_gen.py
-a---           0.00 B             ├── __init__.py
d----           0.00 B     app
-a---           0.00 B         ├── __init__.py
d----           0.00 B         frontend
d----         12.30 KB             templates
-a---         12.30 KB                 ├── swagger_login.html
d----          9.81 KB             static
-a---          1.65 KB                 ├── main.js
-a---          8.16 KB                 ├── logo_anwill.png
d----          8.95 KB         webhooks
-a---          7.40 KB             ├── swagger.py
-a---          1.55 KB             ├── handlers.py
-a---           0.00 B             ├── __init__.py
d----        143.05 KB         docs
-a---          1.92 KB             ├── load_docs.py
-a---         12.63 KB             ├── development.jpg
-a---        128.49 KB             ├── readme_logo.png
-a---           0.00 B             ├── __init__.py
d----          6.00 KB             descriptions
-a---          2.98 KB                 ├── api_description_prod.md
-a---          3.02 KB                 ├── api_description_dev.md
d----           0.00 B         db
-a---           0.00 B             ├── __init__.py
d----         10.11 KB             models
-a---          3.45 KB                 ├── tb_models.py
-a---          6.47 KB                 ├── base.py
-a---         196.00 B                 ├── enums.py
-a---           0.00 B                 ├── __init__.py
d----          5.75 KB             sessions
-a---         817.00 B                 ├── utils.py
-a---          4.89 KB                 ├── _session.py
-a---          65.00 B                 ├── __init__.py
d----          4.44 KB             schemas
-a---          4.44 KB                 ├── tb_schemas.py
-a---           0.00 B                 ├── __init__.py
d----          8.52 KB         core
-a---          8.52 KB             ├── config.py
-a---           0.00 B             ├── __init__.py
d----          4.11 KB         bot
-a---          1.41 KB             ├── decorators.py
-a---          2.70 KB             ├── __init__.py
d----          2.75 KB             middlewares
-a---         671.00 B                 ├── throttling.py
-a---          1.70 KB                 ├── logging.py
-a---         401.00 B                 ├── __init__.py
d----         15.23 KB             handlers
-a---         14.94 KB                 ├── chats.py
-a---         291.00 B                 ├── __init__.py
d----         17.73 KB         utils
-a---          8.12 KB             ├── http_exceptions.py
-a---          9.60 KB             ├── logger.py
-a---           0.00 B             ├── __init__.py
d----         17.43 KB     make-scripts
-a---          5.75 KB         ├── anwill-auto-ssh-linux.sh
-a---          5.29 KB         ├── anwill-auto-ssh.ps1
-a---         465.00 B         ├── anwill-auto-ssh-windows.ps1
-a---          2.41 KB         ├── setup.sh
-a---          2.76 KB         ├── setup.cmd
-a---         781.00 B         ├── anwill-auto-ssh-run-windows.cmd
d----          1.67 KB     deploy
-a---         860.00 B         ├── compose.service.notifier_telebot.app.prod.yml
-a---         854.00 B         ├── compose.service.notifier_telebot.app.dev.yml
d----         12.00 KB     fsm-storage
-a---         12.00 KB         ├── storage.db
