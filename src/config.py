import json
from collections import UserDict

import yaml
from pyaml_env import parse_config

from api import Api
from constants import Service, API_PATHS_LOCATION, BACKUP_DEFAULT_LOCATION, CONFIG_DEFAULT_LOCATION
from models import AppSetting
from utils import ComplexEncoder


class Config(UserDict):
    def __init__(self, services: dict, data: dict = None):
        self._need_to_apply = True
        if not data:  # Initialize empty
            data = {app: {} for app in services}
            self._need_to_apply = False

        base_cfg = parse_config(API_PATHS_LOCATION, default_value='')
        for service, location in services.items():
            api = Api(Service(service), address=location["address"], port=location["port"])
            base_cfg[service] = self._deep_update(base_cfg[service], data[service], api=api)
        super().__init__(base_cfg)

    @classmethod
    def from_yaml(cls, services: dict, filename: str = CONFIG_DEFAULT_LOCATION):
        new_config = parse_config(filename)
        return cls(services=services, data=new_config)

    @staticmethod
    def _deep_update(mapping: dict, updating_mapping: dict, api: Api, prefix: str = '') -> dict:
        for k, v in mapping.items():
            if isinstance(v, dict):  # Nested settings (e.g. config/ui)
                mapping[k] = Config._deep_update(mapping[k], updating_mapping.get(k, {}), api, prefix=f"/{k}")
            elif k in updating_mapping:  # key is in new config, and either list or dict
                if isinstance(updating_mapping[k], list):
                    mapping[k] = AppSetting(updating_mapping[k], resource=f"{prefix}/{k}", api=api)
                elif isinstance(updating_mapping[k], dict):
                    mapping[k] = AppSetting(resource=f"{prefix}/{k}", api=api, **updating_mapping[k])
            else:  # key is not configured in new config, empty AppSetting
                mapping[k] = AppSetting(resource=f"{prefix}/{k}", api=api)
        return mapping

    def apply(self):
        """Apply a Config to running services."""
        def check_and_apply(cfg):
            for item in cfg.values():
                if isinstance(item, AppSetting):
                    item.apply()
                elif isinstance(item, dict):
                    check_and_apply(item)

        if self._need_to_apply:
            check_and_apply(self)
            print('Successfully finished applying configurations.')

    def to_json(self, filename: str):
        with open(filename, 'w') as file:
            json.dump(self.data, file, cls=ComplexEncoder)
        print('Successfully backed-up current configurations.')

    def to_yaml(self, filename: str = BACKUP_DEFAULT_LOCATION):
        with open(filename, 'w') as file:
            yaml.dump(self.data, file, default_flow_style=False)
        print('Successfully backed-up current configurations.')

