def create_ids(dataframe):
        
    # Select only unique NUTS-regions
    unique_locations = dataframe.drop_duplicates(subset=['NUTS_ID'])

    # Create a mapping between unique locations and consecutive integers
    location_mapping = dict(zip(unique_locations['NUTS_ID'], range(1, len(unique_locations) + 1)))
    return location_mapping