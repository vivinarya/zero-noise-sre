from typing import List, Dict, Any, Set
import networkx as nx
from ..ingestion.otel_receiver import SpanData


class TopologyGraphBuilder:
    """Builds a Directed Acyclic Graph (DAG) of microservices dependencies using NetworkX."""

    def __init__(self):
        self.graph = nx.DiGraph()

    def build_from_spans(self, spans: List[SpanData]) -> nx.DiGraph:
        span_lookup: Dict[str, SpanData] = {s.span_id: s for s in spans}

        for span in spans:
            svc = span.service_name
            if not self.graph.has_node(svc):
                self.graph.add_node(svc, operations=set(), error_count=0, call_count=0)

            node_data = self.graph.nodes[svc]
            node_data["operations"].add(span.operation_name)
            node_data["call_count"] += 1
            if span.status_code == "ERROR" or (span.http_status_code and span.http_status_code >= 500):
                node_data["error_count"] += 1

            if span.parent_span_id and span.parent_span_id in span_lookup:
                parent_span = span_lookup[span.parent_span_id]
                parent_svc = parent_span.service_name
                if parent_svc != svc:
                    if not self.graph.has_edge(parent_svc, svc):
                        self.graph.add_edge(parent_svc, svc, call_count=0, error_count=0)
                    edge_data = self.graph.edges[parent_svc, svc]
                    edge_data["call_count"] += 1
                    if span.status_code == "ERROR" or (span.http_status_code and span.http_status_code >= 500):
                        edge_data["error_count"] += 1

        return self.graph

    def get_service_dependencies(self, service_name: str) -> Dict[str, List[str]]:
        if not self.graph.has_node(service_name):
            return {"upstream": [], "downstream": []}

        upstream = list(self.graph.predecessors(service_name))
        downstream = list(self.graph.successors(service_name))
        return {"upstream": upstream, "downstream": downstream}
