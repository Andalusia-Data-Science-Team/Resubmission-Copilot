import asyncio
import json
from typing import Optional

from dotenv import load_dotenv
from llama_cloud import ExtractConfig
from llama_cloud_services import LlamaExtract

from src.resubmission.utils import list_files

_ = load_dotenv()


class ExtractAgent:
    def __init__(
        self, name: str, schema: Optional[str] = None, prompt: Optional[str] = None
    ):
        """
        Generic base class.

        Args:
            name (str): Identifier for the service/object.
            config (dict, optional): Configuration parameters. Defaults to empty dict.
        """
        extractor = LlamaExtract()
        agents = [agent.name for agent in extractor.list_agents()]

        if name in agents:
            print("Loading existing agent.")
            self.agent = extractor.get_agent(name=name)
        elif name not in agents and schema is not None:
            with open(schema, "r") as file:
                schema = json.load(file)
            config = ExtractConfig(
                system_prompt=prompt
                )
            print("Creating new agent.")
            self.agent = extractor.create_agent(
                name=name, data_schema=schema, config=config
            )
        elif name not in agents and schema is None:
            print("No schema found, try again.")

    def extract_file(self, file_path):
        return self.agent.extract(file_path)

    async def extract_batch(self, data_directory):
        files = list_files(data_directory)
        jobs = await self.agent.queue_extraction(files)

        # Check job status
        for job in jobs:
            while True:
                status = self.agent.get_extraction_job(job.id).status
                print(f"Job {job.id}: {status}")
                if status == "SUCCESS":
                    break
                await asyncio.sleep(10)

        # Get results when complete (status = success)
        return [self.agent.get_extraction_run_for_job(job.id) for job in jobs]

    def update_schema(self, new_schema):
        self.agent.data_schema = new_schema
        self.agent.save()
