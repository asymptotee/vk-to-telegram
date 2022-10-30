FROM python:3
WORKDIR /vk-to-telegram
COPY . .
RUN pip install vk_api
RUN pip install pyTelegramBotAPI
CMD ["python", "main.py"]
