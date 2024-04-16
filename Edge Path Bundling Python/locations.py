import pandas as pd
from model import Edge, Node
from IDs import create_ids

def get_locations_data(d):
    # Load data into dataframes
    nodes_list = pd.read_csv("/NUTS2_cents.csv", sep=',', encoding="latin-1") # NUT2-region centroids
    edges_list = pd.read_csv('/OD_movement_DATA.csv', sep=',', encoding="utf-8", usecols=['OD_ID','ORIGIN','DESTINATION','COUNT']) # movement data
    edges_list = edges_list.drop_duplicates(subset=['OD_ID'])
    
    # country selection (if needed, WORK IN PROGRESS)
    #edges_list = edges_list[edges_list['ORIGIN'].str.contains('FI')]
    #edges_list.reset_index(drop=True, inplace=True)
    
    
    nodes = {}
    edges = []
    
    node_ids = create_ids(nodes_list)

    # Load nodes into dict. Maps ID -> Node instance
    for index, row in nodes_list.iterrows():
        idx = node_ids[row['NUTS_ID']]
        name = row['NUTS_ID']
        lat = row['Y']
        long = row['X']
        nodes[idx] = Node(idx, long, lat, name)

    # Load edges to list
    for index, row in edges_list.iterrows():
        so = node_ids[row['ORIGIN']]
        dest = node_ids[row['DESTINATION']]
        od_id = row['OD_ID']
        count = row['COUNT']
        edges.append(Edge(source=so, destination=dest, od_id=od_id, count=count))
    
    # set iterator for edge removal
    calc_r = 0

    # Assign edges to nodes
    for edge in edges:

        # eliminate edges without nodes
        if edge.destination not in nodes or edge.source not in nodes:
            calc_r += 1
            edges.remove(edge)

        source = nodes[edge.source]
        dest = nodes[edge.destination]
        distance = source.distance_to(dest)

        edge.distance = distance
        edge.weight = pow(distance, d)

        source.edges.append(edge)
        dest.edges.append(edge)
    
    # print removed edges
    print('Total number of edges removed: ' + str(calc_r))

    # iterator for removed nodes
    calc_n = 0
    
    # Eliminate nodes without edges
    to_remove = [node.id for node in nodes.values() if len(node.edges) == 0]
    for key in to_remove:
        calc_n += 1
        del nodes[key]
    
    # print removed node count
    print('Nodes removed: '+str(calc_n))
    
    # print nodes values
    #print(nodes.values())

    # Sort edges inside nodes in ascending order
    for node in nodes.values():
        node.edges.sort(key=lambda x: x.distance)

    # Sort edges
    edges.sort(key=lambda x: x.weight, reverse=True)
    print(edges[0].source)
    print(edges[0].destination)
    print(edges[0].od_id)
    print('Origin node name: ' + str(nodes[edges[0].source].name) + ' , origin node id: ' + str(nodes[edges[0].source].id) + '\nDestination node name: ' + str(nodes[edges[0].destination].name) + ', dest origin id: ' + str(nodes[edges[0].destination].id))
    return nodes, edges