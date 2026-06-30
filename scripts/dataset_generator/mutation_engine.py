import importlib
import pkgutil
from typing import Dict, Any, List

class MutationEngine:
    def __init__(self):
        self.plugins = []
        self._load_plugins()
        
    def _load_plugins(self):
        import scripts.dataset_generator.mutations as mutations_pkg
        from scripts.dataset_generator.mutations.base import BaseMutation
        
        for _, module_name, _ in pkgutil.iter_modules(mutations_pkg.__path__):
            if module_name == "base":
                continue
            module = importlib.import_module(f"scripts.dataset_generator.mutations.{module_name}")
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if isinstance(attr, type) and issubclass(attr, BaseMutation) and attr is not BaseMutation:
                    self.plugins.append(attr())
                    
    def apply_mutations(self, record: Dict[str, Any], source_type: str, profile_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Applies configured mutations for a specific source_type (e.g. 'pdf', 'csv').
        Returns a list of mutation metadata dictionaries for tracking in evaluation_mapping.json.
        """
        source_config = profile_config.get(source_type, {})
        applied_mutations = []
        
        for plugin in self.plugins:
            plugin_config = source_config.get(plugin.mutation_type, {})
            if not plugin_config:
                continue
                
            mutations_made = plugin.apply(record, plugin_config)
            for field, details in mutations_made.items():
                applied_mutations.append({
                    "type": plugin.mutation_type,
                    "field": field,
                    **details
                })
                
        return applied_mutations
