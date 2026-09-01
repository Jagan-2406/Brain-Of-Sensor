def get_zone(x_center, frame_width):
    """
    Returns 'zone_1' if x_center is in the left half,
    'zone_2' if in the right half.
    """
    if x_center < frame_width / 2:
        return "zone_1"
    else:
        return "zone_2"
