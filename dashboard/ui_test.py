import streamlit as st
import altair as alt
import polars as pl
import time

def run_ui_tests():
    """Run UI interaction tests to verify that controls are working."""
    st.subheader("UI Interaction Tests")

    # Test 1: Simple button click
    st.write("Test 1: Button Click")
    if st.button("Click Me"):
        st.success("Button clicked successfully!")

    # Test 2: Tooltip hover
    st.write("Test 2: Chart Tooltip")
    data = pl.DataFrame({
        'x': range(10),
        'y': range(10),
        'label': [f"Point {i}" for i in range(10)]
    })

    chart = alt.Chart(data).mark_circle(size=100).encode(
        x='x',
        y='y',
        tooltip=['label', 'x', 'y']
    ).properties(width=400, height=200).interactive()

    st.altair_chart(chart, use_container_width=True)
    st.caption("Hover over points to see tooltips")

    # Test 3: Simple tabs
    st.write("Test 3: Tabs")
    test_tabs = st.tabs(["Tab A", "Tab B", "Tab C"])
    with test_tabs[0]:
        st.write("Content of Tab A")
    with test_tabs[1]:
        st.write("Content of Tab B")
    with test_tabs[2]:
        st.write("Content of Tab C")

    # Test 4: Session state persistence
    st.write("Test 4: Session State")
    if 'counter' not in st.session_state:
        st.session_state.counter = 0

    if st.button("Increment Counter"):
        st.session_state.counter += 1

    st.write(f"Counter value: {st.session_state.counter}")

    # Add timestamp to show page is responsive
    st.caption(f"Last updated: {time.strftime('%H:%M:%S')}")