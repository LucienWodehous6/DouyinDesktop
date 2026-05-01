from openai import OpenAI

client = OpenAI(api_key="sk-ekwgvkrmrzodccqkpwvsfkotztboyzrfxfcscbkhggfuavlo", base_url="https://api.siliconflow.cn/v1")

response = client.images.generate(
    model="Kwai-Kolors/Kolors",
    prompt="a cat",
    size="1024x1024",
    n=1,
    extra_body={
        "step": 20
    }
)

print(response)