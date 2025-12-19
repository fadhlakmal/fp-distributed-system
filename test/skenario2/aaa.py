def verify_data_consistency(self) -> None:
    counts = {}
    for node_name in self.nodes.keys():
        with self.get_connection(node_name, silent=True) as conn:
            cursor.execute("SELECT COUNT(*) as count FROM transactions")
            counts[node_name] = result[0]
    
    values = [v for v in counts.values() if v is not None]
    if len(set(values)) == 1 and len(values) == len(self.nodes):
        print("✅ Data is consistent across all nodes!")