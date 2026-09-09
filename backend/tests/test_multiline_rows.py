from app.document_ai.layout.inference import TextFragment, cluster_fragments_by_y, collapse_multiline_rows


def test_y_axis_clustering_keeps_same_visual_line_together() -> None:
    fragments = [
        TextFragment("Widget", 10, 100, 80, 112, 0),
        TextFragment("2", 210, 101, 220, 112, 1),
        TextFragment("with premium support", 10, 116, 150, 128, 0),
        TextFragment("200", 260, 101, 290, 112, 2),
    ]
    lines = cluster_fragments_by_y(fragments)
    assert len(lines) == 2
    assert [item.text for item in lines[0]] == ["Widget", "2", "200"]


def test_description_fragments_collapse_into_one_logical_row() -> None:
    rows = [
        ["Description", "Qty", "Total"],
        ["Widget", "2", "200"],
        ["with premium support", "", ""],
        ["Another item", "1", "50"],
    ]
    collapsed = collapse_multiline_rows(rows)
    assert collapsed == [
        ["Description", "Qty", "Total"],
        ["Widget\nwith premium support", "2", "200"],
        ["Another item", "1", "50"],
    ]
