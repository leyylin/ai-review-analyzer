import streamlit as st

try:
    from gigachat import GigaChat
    from gigachat.exceptions import AuthenticationError, GigaChatException, NotFoundError
except ImportError:
    GigaChat = None
    AuthenticationError = GigaChatException = NotFoundError = Exception


st.set_page_config(
    page_title="📊 AI Review Analyzer",
    page_icon="📊",
    layout="wide",
)


PROMPT_TEMPLATE = """Ты — опытный AI-аналитик отзывов и обращений клиентов в маркетинговом агентстве.

Проанализируй приведённый ниже массив отзывов/обращений и верни ответ СТРОГО на русском языке
в формате Markdown со следующими разделами:

## 1. Общая тональность
Укажи одну из оценок: **Позитивная**, **Нейтральная** или **Негативная**, и кратко обоснуй (2-3 предложения).

## 2. Ключевые проблемы / боли клиентов
Оформи маркированным списком. Для каждой проблемы укажи, насколько часто она встречается (часто / иногда / единично).

## 3. Рекомендации для отдела маркетинга и продаж
Дай 3-5 конкретных, выполнимых рекомендаций.

## 4. Шаблон ответа клиенту
Приведи готовый вежливый и профессиональный шаблон ответа клиенту.

Если данных недостаточно для какого-то раздела — честно напиши об этом, не выдумывай факты.

Отзывы/обращения:
---
{feedback}
---
"""

FALLBACK_MODELS = ["GigaChat-2", "GigaChat-2-Pro", "GigaChat-Max", "GigaChat"]

SCOPES = {
    "GIGACHAT_API_PERS (личный ключ)": "GIGACHAT_API_PERS",
    "GIGACHAT_API_RU (коммерческий ключ)": "GIGACHAT_API_RU",
    "GIGACHAT_API_B2B": "GIGACHAT_API_B2B",
    "GIGACHAT_API_CORP": "GIGACHAT_API_CORP",
}


@st.cache_data(show_spinner=False, ttl=3600)
def fetch_models(api_key: str, scope: str) -> list:
    """Вернуть список моделей, доступных для ключа."""
    with GigaChat(
        credentials=api_key,
        scope=scope,
        verify_ssl_certs=False,
    ) as giga:
        response = giga.get_models()
        return sorted({m.id_ for m in response.data})


def analyze(feedback: str, api_key: str, scope: str, model: str) -> str:
    with GigaChat(
        credentials=api_key,
        scope=scope,
        model=model,
        verify_ssl_certs=False,
    ) as giga:
        response = giga.chat(PROMPT_TEMPLATE.format(feedback=feedback))
        return response.choices[0].message.content


st.sidebar.header("⚙️ Настройки ИИ")
st.sidebar.caption("Введите ключ доступа GigaChat, чтобы включить анализ.")
api_key = st.sidebar.text_input(
    "GigaChat API Key (OAuth-токен)",
    type="password",
    placeholder="Введите токен...",
    help="Получить токен: https://developers.sberbank.ru",
)
scope_label = st.sidebar.selectbox("Scope (тип ключа)", list(SCOPES.keys()))
scope = SCOPES[scope_label]

st.sidebar.markdown("---")

model_options = []
if api_key and GigaChat is not None:
    try:
        model_options = fetch_models(api_key, scope)
    except AuthenticationError:
        st.sidebar.error("❌ Токен отклонён. Проверьте ключ и scope.")
    except GigaChatException as exc:
        st.sidebar.warning(f"Не удалось получить список моделей: {exc}")
    except Exception as exc:
        st.sidebar.warning(f"Не удалось получить список моделей: {exc}")

if model_options:
    st.sidebar.success(f"✅ Доступно моделей: {len(model_options)}")
    model_name = st.sidebar.selectbox("Модель", model_options, index=0)
else:
    st.sidebar.info("Список моделей подтянется после ввода ключа.")
    model_name = st.sidebar.selectbox("Модель", FALLBACK_MODELS, index=0)

st.sidebar.markdown("---")
st.sidebar.markdown(
    "**Как получить токен:**\n"
    "1. Зарегистрируйтесь на [SberBank API Portal](https://developers.sberbank.ru)\n"
    "2. Создайте приложение → «Авторизация» → «Запросить токен»\n"
    "3. Скопируйте токен и вставьте его в поле выше"
)

st.title("📊 AI Review Analyzer")
st.markdown(
    "Внутренний инструмент маркетинговой команды для быстрого анализа "
    "отзывов и обращений клиентов. Вставьте тексты — ИИ выделит тональность, "
    "боли клиентов, даст рекомендации и шаблон ответа."
)

feedback = st.text_area(
    "Вставьте отзывы или обращения клиентов (по одному на строку):",
    height=260,
    placeholder=(
        "Отличный сервис, всё понравилось, но доставка задержалась на 3 дня.\n"
        "Не дозвониться до поддержки уже второй день!\n"
        "Спасибо менеджеру Анне за оперативную помощь."
    ),
)

analyze_clicked = st.button("🚀 Запустить анализ", type="primary", use_container_width=True)

if analyze_clicked:
    if not api_key:
        st.error("❌ Не указан ключ GigaChat. Введите его в боковой панели слева.")
    elif not feedback.strip():
        st.warning("⚠️ Вставьте хотя бы один отзыв или обращение для анализа.")
    elif GigaChat is None:
        st.error(
            "❌ Библиотека `gigachat` не установлена.\n\n"
            "Выполните в терминале: `pip install gigachat`"
        )
    else:
        try:
            with st.spinner(f"🧠 ИИ ({model_name}) анализирует отзывы..."):
                result = analyze(feedback, api_key, scope, model_name)
            st.success("✅ Анализ готов!")
            st.markdown("---")
            st.markdown(result)
        except AuthenticationError:
            st.error(
                "❌ GigaChat не принял ключ доступа (ошибка авторизации).\n\n"
                "Проверьте токен и выбранный scope в боковой панели."
            )
        except NotFoundError:
            st.error(
                f"❌ Модель **{model_name}** недоступна для вашего ключа (404 No such model).\n\n"
                "Выберите другую модель в боковой панели — список моделей "
                "автоматически подтягивается из API для вашего токена."
            )
        except GigaChatException as exc:
            st.error(f"❌ Ошибка сервиса GigaChat: `{exc}`")
        except Exception as exc:
            st.error(
                "❌ Не удалось получить ответ от GigaChat.\n\n"
                f"**Детали ошибки:** `{exc}`\n\n"
                "Проверьте ключ, лимиты квоты и подключение к интернету."
            )

st.markdown("---")
with st.expander("📖 Как запустить приложение"):
    st.markdown(
        "**1. Установите зависимости:**\n"
        "```bash\n"
        "pip install streamlit gigachat\n"
        "```\n\n"
        "**2. Запустите приложение:**\n"
        "```bash\n"
        "streamlit run app.py\n"
        "```\n\n"
        "**3. Откройте браузер** по адресу, который покажет Streamlit "
        "(обычно http://localhost:8501), введите токен GigaChat в боковой панели, "
        "выберите модель из списка и нажмите «Запустить анализ»."
    )
