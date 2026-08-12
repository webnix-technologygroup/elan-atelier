from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("studio", "0003_expand_journal_articles")]

    operations = [
        migrations.CreateModel(
            name="FAQ",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("question", models.CharField(max_length=240, verbose_name="Вопрос")),
                ("answer", models.TextField(verbose_name="Ответ")),
                (
                    "order",
                    models.PositiveSmallIntegerField(default=0, verbose_name="Порядок"),
                ),
                (
                    "is_active",
                    models.BooleanField(default=True, verbose_name="Показывать"),
                ),
            ],
            options={
                "verbose_name": "частый вопрос",
                "verbose_name_plural": "Частые вопросы",
                "ordering": ["order", "id"],
            },
        ),
        migrations.CreateModel(
            name="SiteAsset",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "section",
                    models.CharField(
                        choices=[
                            ("global", "Общие настройки"),
                            ("home", "Главная"),
                            ("services", "Услуги"),
                            ("about", "О нас"),
                            ("team", "Команда"),
                            ("journal", "Журнал"),
                            ("contacts", "Контакты"),
                            ("booking", "Запись"),
                            ("cabinet", "Личный кабинет"),
                            ("privacy", "Конфиденциальность"),
                            ("errors", "Ошибки"),
                        ],
                        max_length=30,
                        verbose_name="Раздел",
                    ),
                ),
                (
                    "key",
                    models.SlugField(
                        max_length=100, unique=True, verbose_name="Системный ключ"
                    ),
                ),
                (
                    "label",
                    models.CharField(
                        max_length=160, verbose_name="Название изображения"
                    ),
                ),
                (
                    "file",
                    models.FileField(
                        blank=True, upload_to="site/", verbose_name="Загруженный файл"
                    ),
                ),
                (
                    "fallback_path",
                    models.CharField(
                        blank=True,
                        help_text="Например: studio/img/hero.svg",
                        max_length=200,
                        verbose_name="Резервный файл из static",
                    ),
                ),
                (
                    "order",
                    models.PositiveSmallIntegerField(default=0, verbose_name="Порядок"),
                ),
            ],
            options={
                "verbose_name": "изображение сайта",
                "verbose_name_plural": "Изображения сайта",
                "ordering": ["section", "order", "key"],
            },
        ),
        migrations.CreateModel(
            name="SiteText",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "section",
                    models.CharField(
                        choices=[
                            ("global", "Общие настройки"),
                            ("home", "Главная"),
                            ("services", "Услуги"),
                            ("about", "О нас"),
                            ("team", "Команда"),
                            ("journal", "Журнал"),
                            ("contacts", "Контакты"),
                            ("booking", "Запись"),
                            ("cabinet", "Личный кабинет"),
                            ("privacy", "Конфиденциальность"),
                            ("errors", "Ошибки"),
                        ],
                        max_length=30,
                        verbose_name="Раздел",
                    ),
                ),
                (
                    "key",
                    models.SlugField(
                        max_length=100, unique=True, verbose_name="Системный ключ"
                    ),
                ),
                (
                    "label",
                    models.CharField(max_length=160, verbose_name="Название поля"),
                ),
                ("value", models.TextField(blank=True, verbose_name="Текст")),
                (
                    "order",
                    models.PositiveSmallIntegerField(default=0, verbose_name="Порядок"),
                ),
            ],
            options={
                "verbose_name": "текст сайта",
                "verbose_name_plural": "Тексты сайта",
                "ordering": ["section", "order", "key"],
            },
        ),
        migrations.AddField(
            model_name="service",
            name="uploaded_icon",
            field=models.FileField(blank=True, upload_to="services/"),
        ),
        migrations.AddField(
            model_name="teammember",
            name="uploaded_image",
            field=models.FileField(blank=True, upload_to="team/"),
        ),
        migrations.AddField(
            model_name="article",
            name="uploaded_image",
            field=models.FileField(blank=True, upload_to="journal/"),
        ),
        migrations.AlterModelOptions(
            name="service",
            options={
                "ordering": ["order"],
                "verbose_name": "услуга",
                "verbose_name_plural": "Услуги",
            },
        ),
        migrations.AlterModelOptions(
            name="teammember",
            options={
                "ordering": ["order"],
                "verbose_name": "мастер",
                "verbose_name_plural": "Команда",
            },
        ),
        migrations.AlterModelOptions(
            name="article",
            options={
                "ordering": ["-published_at"],
                "verbose_name": "статья",
                "verbose_name_plural": "Статьи журнала",
            },
        ),
    ]
