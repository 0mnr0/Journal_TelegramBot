import re

import g4f
from g4f.client import Client
from openai import OpenAI

routerclient = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key=open("router.ai","r").read(),
)


class WalkingTowardsTheRiver:
    def __init__(self):
        pass

    @staticmethod
    def GenerateTextOld(prompt):
        client = Client()
        prov = g4f.Provider.DDG
        response = (client.chat.completions.create(
            model="gpt-4",
            provider=prov,
            messages=[{"role": "user", "content": prompt}],
        ))

        return str(response.choices[0].message.content)
    @staticmethod
    def GenerateTextExtra(prompt):
        client = Client()
        response = (client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
        ))

        return str(response.choices[0].message.content)

    @staticmethod
    def ThinkAbout(prompt, useCodeCleaner=False):
        def CodeCleaner(text: str) -> str:
            return re.sub(r'```[^\s]*', '', text)

        try:
            completion = routerclient.chat.completions.create(
                extra_body={},
                model="deepseek/deepseek-r1-distill-llama-70b:free",
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            return str(CodeCleaner(completion.choices[0].message.content)) if useCodeCleaner else str(completion.choices[0].message.content)
        except Exception as e:
            print("deepseek failed!", e)
            return str(CodeCleaner(WalkingTowardsTheRiver.GenerateTextExtra(prompt))) if useCodeCleaner else str(WalkingTowardsTheRiver.GenerateTextExtra(prompt))

    @staticmethod
    def GenerateImage(prompt):
        client = Client()

        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            provider=g4f.Provider.AIChatFree,
            response_format="url"
        )

        return response.data[0].url

