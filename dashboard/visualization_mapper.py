import altair as alt
import polars as pl
from typing import Dict, Any, List, Optional
from dashboard.chart_config import ChartConfig, CHART_CONFIGS
from dashboard.components import format_duration_tooltip, SPOTIFY_GREEN, CATEGORY_COLORS

class SQLVisualizationMapper:
    """Maps SQL query results to appropriate visualizations based on data structure."""

    def __init__(self):
        """Initialize the visualization mapper."""
        self.chart_config = ChartConfig()

    def map_to_visualization(
        self,
        data: List[Dict[str, Any]],
        analysis_type: str,
        visualization_spec: Dict[str, Any]
    ) -> alt.Chart:
        """
        Map SQL query results to an appropriate visualization.

        Args:
            data: The SQL query results as a list of dictionaries
            analysis_type: The type of analysis (e.g., "aggregation", "trend", "comparison")
            visualization_spec: Specification for the visualization

        Returns:
            alt.Chart: An Altair chart configured for the data
        """
        if not data:
            return None

        # Convert to Polars DataFrame for consistent processing
        df = pl.DataFrame(data)

        # Extract visualization type from spec
        viz_type = visualization_spec.get("type", "bar").lower()
        dimensions = visualization_spec.get("dimensions", {})

        # Determine chart type and apply appropriate visualization
        if viz_type in ["bar", "stacked bar"]:
            return self._create_bar_chart(df, dimensions)
        elif viz_type == "line":
            return self._create_line_chart(df, dimensions)
        elif viz_type == "scatter":
            return self._create_scatter_chart(df, dimensions)
        elif viz_type == "pie" or viz_type == "donut":
            return self._create_pie_chart(df, dimensions)
        elif viz_type == "heatmap":
            return self._create_heatmap(df, dimensions)
        elif viz_type == "area":
            return self._create_area_chart(df, dimensions)
        elif viz_type == "polar":
            return self._create_polar_chart(df, dimensions)
        elif viz_type == "ridgeline":
            return self._create_ridgeline_plot(df, dimensions)
        else:
            # Default to bar chart
            return self._create_bar_chart(df, dimensions)

    def _add_tooltips(self, df: pl.DataFrame) -> pl.DataFrame:
        """Add tooltip columns if they don't exist."""
        if 'total_ms' in df.columns and 'duration_tooltip' not in df.columns:
            return df.with_columns([
                pl.col('total_ms').map_elements(
                    format_duration_tooltip,
                    return_dtype=pl.Utf8
                ).alias('duration_tooltip')
            ])
        return df

    def _create_bar_chart(self, df: pl.DataFrame, dimensions: Dict[str, Any]) -> alt.Chart:
        """Create a bar chart based on dimensions."""
        df = self._add_tooltips(df)

        # Extract dimension fields
        x_field = dimensions.get("x", {}).get("field")
        y_field = dimensions.get("y", {}).get("field")
        color_field = dimensions.get("color", {}).get("field")

        if not x_field or not y_field:
            # Use first numeric column as x and first non-numeric as y if not specified
            numeric_cols = [col for col in df.columns if df[col].dtype in (pl.Float64, pl.Int64)]
            other_cols = [col for col in df.columns if col not in numeric_cols]

            x_field = x_field or (numeric_cols[0] if numeric_cols else df.columns[0])
            y_field = y_field or (other_cols[0] if other_cols else df.columns[1])

        # Determine types
        x_type = dimensions.get("x", {}).get("type", "quantitative")[0]
        y_type = dimensions.get("y", {}).get("type", "nominal")[0]

        # Create encodings
        encodings = {
            "x": alt.X(f"{x_field}:{x_type}", title=x_field),
            "y": alt.Y(f"{y_field}:{y_type}", title=y_field, sort="-x")
        }

        # Add color encoding if specified
        if color_field:
            color_type = dimensions.get("color", {}).get("type", "nominal")[0]
            encodings["color"] = alt.Color(
                f"{color_field}:{color_type}",
                scale=CATEGORY_COLORS
            )

        # Build tooltips based on all columns
        tooltip_fields = [
            alt.Tooltip(f"{col}:{self._infer_field_type(df[col])}")
            for col in df.columns
        ]
        encodings["tooltip"] = tooltip_fields

        # Create chart with dynamic height based on data
        height = self.chart_config.calculate_height(len(df))

        chart = alt.Chart(df).mark_bar(color=SPOTIFY_GREEN).encode(
            **encodings
        ).properties(
            height=height,
            **self.chart_config.create_base_chart_config()
        ).interactive()

        return chart

    def _create_line_chart(self, df: pl.DataFrame, dimensions: Dict[str, Any]) -> alt.Chart:
        """Create a line chart based on dimensions."""
        df = self._add_tooltips(df)

        # Extract dimension fields
        x_field = dimensions.get("x", {}).get("field")
        y_field = dimensions.get("y", {}).get("field")
        color_field = dimensions.get("color", {}).get("field")

        if not x_field or not y_field:
            # Use first date/time column as x and first numeric as y if not specified
            date_cols = [col for col in df.columns if df[col].dtype in (pl.Date, pl.Datetime)]
            numeric_cols = [col for col in df.columns if df[col].dtype in (pl.Float64, pl.Int64)]

            x_field = x_field or (date_cols[0] if date_cols else df.columns[0])
            y_field = y_field or (numeric_cols[0] if numeric_cols else df.columns[1])

        # Determine types
        x_type = dimensions.get("x", {}).get("type", "temporal")[0]
        y_type = dimensions.get("y", {}).get("type", "quantitative")[0]

        # Create encodings
        encodings = {
            "x": alt.X(f"{x_field}:{x_type}", title=x_field),
            "y": alt.Y(f"{y_field}:{y_type}", title=y_field)
        }

        # Add color encoding if specified
        if color_field:
            color_type = dimensions.get("color", {}).get("type", "nominal")[0]
            encodings["color"] = alt.Color(
                f"{color_field}:{color_type}",
                scale=CATEGORY_COLORS
            )

        # Build tooltips based on all columns
        tooltip_fields = [
            alt.Tooltip(f"{col}:{self._infer_field_type(df[col])}")
            for col in df.columns
        ]
        encodings["tooltip"] = tooltip_fields

        chart = alt.Chart(df).mark_line(point=True).encode(
            **encodings
        ).properties(
            height=400,
            **self.chart_config.create_base_chart_config()
        ).interactive()

        return chart

    def _create_scatter_chart(self, df: pl.DataFrame, dimensions: Dict[str, Any]) -> alt.Chart:
        """Create a scatter chart based on dimensions."""
        df = self._add_tooltips(df)

        # Extract dimension fields
        x_field = dimensions.get("x", {}).get("field")
        y_field = dimensions.get("y", {}).get("field")
        color_field = dimensions.get("color", {}).get("field")
        size_field = dimensions.get("size", {}).get("field")

        # Get numeric columns for x and y if not specified
        numeric_cols = [col for col in df.columns if df[col].dtype in (pl.Float64, pl.Int64)]

        x_field = x_field or (numeric_cols[0] if len(numeric_cols) > 0 else df.columns[0])
        y_field = y_field or (numeric_cols[1] if len(numeric_cols) > 1 else df.columns[1])

        # Determine types
        x_type = dimensions.get("x", {}).get("type", "quantitative")[0]
        y_type = dimensions.get("y", {}).get("type", "quantitative")[0]

        # Create encodings
        encodings = {
            "x": alt.X(f"{x_field}:{x_type}", title=x_field),
            "y": alt.Y(f"{y_field}:{y_type}", title=y_field)
        }

        # Add color encoding if specified
        if color_field:
            color_type = dimensions.get("color", {}).get("type", "nominal")[0]
            encodings["color"] = alt.Color(
                f"{color_field}:{color_type}",
                scale=CATEGORY_COLORS
            )

        # Add size encoding if specified
        if size_field:
            size_type = dimensions.get("size", {}).get("type", "quantitative")[0]
            encodings["size"] = alt.Size(
                f"{size_field}:{size_type}"
            )

        # Build tooltips
        tooltip_fields = [
            alt.Tooltip(f"{col}:{self._infer_field_type(df[col])}")
            for col in df.columns
        ]
        encodings["tooltip"] = tooltip_fields

        chart = alt.Chart(df).mark_circle(opacity=0.7).encode(
            **encodings
        ).properties(
            height=400,
            **self.chart_config.create_base_chart_config()
        ).interactive()

        return chart

    def _create_pie_chart(self, df: pl.DataFrame, dimensions: Dict[str, Any]) -> alt.Chart:
        """Create a pie chart based on dimensions."""
        df = self._add_tooltips(df)

        # For pie charts, we need a category and a value
        theta_field = dimensions.get("y", {}).get("field")
        color_field = dimensions.get("x", {}).get("field") or dimensions.get("color", {}).get("field")

        # If not specified, find appropriate columns
        numeric_cols = [col for col in df.columns if df[col].dtype in (pl.Float64, pl.Int64)]
        other_cols = [col for col in df.columns if col not in numeric_cols]

        theta_field = theta_field or (numeric_cols[0] if numeric_cols else df.columns[1])
        color_field = color_field or (other_cols[0] if other_cols else df.columns[0])

        # Create the pie chart
        chart = alt.Chart(df).mark_arc().encode(
            theta=alt.Theta(f"{theta_field}:Q"),
            color=alt.Color(
                f"{color_field}:N",
                scale=CATEGORY_COLORS
            ),
            tooltip=[
                alt.Tooltip(f"{col}:{self._infer_field_type(df[col])}")
                for col in df.columns
            ]
        ).properties(
            height=400,
            width=400
        ).interactive()

        return chart

    def _create_heatmap(self, df: pl.DataFrame, dimensions: Dict[str, Any]) -> alt.Chart:
        """Create a heatmap based on dimensions."""
        df = self._add_tooltips(df)

        # Extract dimension fields
        x_field = dimensions.get("x", {}).get("field")
        y_field = dimensions.get("y", {}).get("field")
        color_field = dimensions.get("color", {}).get("field")

        # If not specified, find appropriate columns
        if not x_field or not y_field or not color_field:
            numeric_cols = [col for col in df.columns if df[col].dtype in (pl.Float64, pl.Int64)]
            other_cols = [col for col in df.columns if col not in numeric_cols]

            x_field = x_field or (other_cols[0] if other_cols else df.columns[0])
            y_field = y_field or (other_cols[1] if len(other_cols) > 1 else df.columns[1])
            color_field = color_field or (numeric_cols[0] if numeric_cols else df.columns[2])

        # Determine types
        x_type = dimensions.get("x", {}).get("type", "ordinal")[0]
        y_type = dimensions.get("y", {}).get("type", "ordinal")[0]
        color_type = dimensions.get("color", {}).get("type", "quantitative")[0]

        # Create the heatmap
        chart = alt.Chart(df).mark_rect().encode(
            x=alt.X(f"{x_field}:{x_type}", title=x_field),
            y=alt.Y(f"{y_field}:{y_type}", title=y_field),
            color=alt.Color(
                f"{color_field}:{color_type}",
                scale=alt.Scale(scheme="viridis")
            ),
            tooltip=[
                alt.Tooltip(f"{col}:{self._infer_field_type(df[col])}")
                for col in df.columns
            ]
        ).properties(
            height=400,
            **self.chart_config.create_base_chart_config()
        ).interactive()

        return chart

    def _create_area_chart(self, df: pl.DataFrame, dimensions: Dict[str, Any]) -> alt.Chart:
        """Create an area chart based on dimensions."""
        df = self._add_tooltips(df)

        # Extract dimension fields
        x_field = dimensions.get("x", {}).get("field")
        y_field = dimensions.get("y", {}).get("field")
        color_field = dimensions.get("color", {}).get("field")

        # If not specified, find appropriate columns
        date_cols = [col for col in df.columns if df[col].dtype in (pl.Date, pl.Datetime)]
        numeric_cols = [col for col in df.columns if df[col].dtype in (pl.Float64, pl.Int64)]

        x_field = x_field or (date_cols[0] if date_cols else df.columns[0])
        y_field = y_field or (numeric_cols[0] if numeric_cols else df.columns[1])

        # Determine types
        x_type = dimensions.get("x", {}).get("type", "temporal")[0]
        y_type = dimensions.get("y", {}).get("type", "quantitative")[0]

        # Create encodings
        encodings = {
            "x": alt.X(f"{x_field}:{x_type}", title=x_field),
            "y": alt.Y(f"{y_field}:{y_type}", title=y_field)
        }

        # Add color encoding if specified
        if color_field:
            color_type = dimensions.get("color", {}).get("type", "nominal")[0]
            encodings["color"] = alt.Color(
                f"{color_field}:{color_type}",
                scale=CATEGORY_COLORS
            )

        # Build tooltips
        tooltip_fields = [
            alt.Tooltip(f"{col}:{self._infer_field_type(df[col])}")
            for col in df.columns
        ]
        encodings["tooltip"] = tooltip_fields

        chart = alt.Chart(df).mark_area(
            opacity=0.7,
            interpolate='monotone'
        ).encode(
            **encodings
        ).properties(
            height=400,
            **self.chart_config.create_base_chart_config()
        ).interactive()

        return chart

    def _create_polar_chart(self, df: pl.DataFrame, dimensions: Dict[str, Any]) -> alt.Chart:
        """Create a polar chart (radial bar chart) based on dimensions."""
        df = self._add_tooltips(df)

        # For polar charts, typically need an angle and a radius
        angle_field = dimensions.get("x", {}).get("field")
        radius_field = dimensions.get("y", {}).get("field")
        color_field = dimensions.get("color", {}).get("field")

        # If not specified, find appropriate columns
        numeric_cols = [col for col in df.columns if df[col].dtype in (pl.Float64, pl.Int64)]
        other_cols = [col for col in df.columns if col not in numeric_cols]

        angle_field = angle_field or (other_cols[0] if other_cols else df.columns[0])
        radius_field = radius_field or (numeric_cols[0] if numeric_cols else df.columns[1])

        # Create the polar chart - convert to radial coordinates
        polar_df = df.clone()

        # Create encodings
        encodings = {
            "theta": alt.Theta(f"{angle_field}:N", sort=None),
            "radius": alt.Radius(f"{radius_field}:Q")
        }

        # Add color encoding if specified
        if color_field:
            color_type = dimensions.get("color", {}).get("type", "nominal")[0]
            encodings["color"] = alt.Color(
                f"{color_field}:{color_type}",
                scale=CATEGORY_COLORS
            )
        else:
            encodings["color"] = alt.Color(f"{angle_field}:N", scale=CATEGORY_COLORS)

        # Build tooltips
        tooltip_fields = [
            alt.Tooltip(f"{col}:{self._infer_field_type(df[col])}")
            for col in df.columns
        ]
        encodings["tooltip"] = tooltip_fields

        chart = alt.Chart(polar_df).mark_arc(innerRadius=20).encode(
            **encodings
        ).properties(
            height=400,
            width=400
        ).interactive()

        return chart

    def _create_ridgeline_plot(self, df: pl.DataFrame, dimensions: Dict[str, Any]) -> alt.Chart:
        """Create a ridgeline plot based on dimensions."""
        # Ridgeline plots need density transforms which are more advanced
        # For now, we'll create a grouped area chart as a simplified version

        df = self._add_tooltips(df)

        # Extract dimension fields
        x_field = dimensions.get("x", {}).get("field")
        y_field = dimensions.get("y", {}).get("field")
        color_field = dimensions.get("color", {}).get("field") or y_field

        # If not specified, find appropriate columns
        numeric_cols = [col for col in df.columns if df[col].dtype in (pl.Float64, pl.Int64)]
        other_cols = [col for col in df.columns if col not in numeric_cols]

        x_field = x_field or (numeric_cols[0] if numeric_cols else df.columns[0])
        y_field = y_field or (other_cols[0] if other_cols else df.columns[1])

        # Determine types
        x_type = dimensions.get("x", {}).get("type", "quantitative")[0]
        y_type = dimensions.get("y", {}).get("type", "ordinal")[0]

        # Create the chart with a hack to approximate ridgeline effect
        chart = alt.Chart(df).mark_area(
            opacity=0.7,
            interpolate='monotone'
        ).encode(
            x=alt.X(f"{x_field}:{x_type}", title=x_field),
            y=alt.Y(f"{y_field}:{y_type}", title=y_field),
            color=alt.Color(f"{color_field}:N", scale=CATEGORY_COLORS),
            tooltip=[
                alt.Tooltip(f"{col}:{self._infer_field_type(df[col])}")
                for col in df.columns
            ]
        ).properties(
            height=400,
            **self.chart_config.create_base_chart_config()
        ).interactive()

        return chart

    def _infer_field_type(self, series: pl.Series) -> str:
        """Infer the Altair field type from a polars series."""
        dtype = series.dtype

        if dtype in (pl.Date, pl.Datetime):
            return "T"
        elif dtype in (pl.Float64, pl.Int64):
            return "Q"
        elif dtype == pl.Boolean:
            return "N"
        else:
            return "N"  # Default to nominal for strings and others