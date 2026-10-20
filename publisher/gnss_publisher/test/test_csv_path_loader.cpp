#include <gtest/gtest.h>

#include <sstream>
#include <stdexcept>

#include "gnss_publisher/csv_path_loader.hpp"

using gnss_publisher::load_path_csv;
using gnss_publisher::parse_path_csv;

namespace
{

gnss_publisher::PathLoadResult parse(const std::string & text)
{
  std::istringstream in(text);
  return parse_path_csv(in);
}

}  // namespace

TEST(CsvPathLoader, ParsesHeaderAndRows)
{
  const auto result = parse("latitude,longitude,altitude\n22.6166,120.279,0.0\n22.617,120.2745,1.5\n");
  ASSERT_EQ(result.points.size(), 2u);
  EXPECT_DOUBLE_EQ(result.points[0].latitude, 22.6166);
  EXPECT_DOUBLE_EQ(result.points[0].longitude, 120.279);
  EXPECT_DOUBLE_EQ(result.points[1].altitude, 1.5);
  EXPECT_TRUE(result.warnings.empty());
}

TEST(CsvPathLoader, AltitudeIsOptionalAndHeaderIsOptional)
{
  const auto result = parse("22.6,120.2\n22.7,120.3\n");
  ASSERT_EQ(result.points.size(), 2u);
  EXPECT_DOUBLE_EQ(result.points[0].altitude, 0.0);
}

TEST(CsvPathLoader, SkipsBlankLinesCommentsAndCrlf)
{
  const auto result = parse("# generated\r\n\r\nlat , lon\r\n  22.6 , 120.2 \r\n\r\n");
  ASSERT_EQ(result.points.size(), 1u);
  EXPECT_DOUBLE_EQ(result.points[0].longitude, 120.2);
  EXPECT_TRUE(result.warnings.empty());
}

TEST(CsvPathLoader, SkipsMalformedAndOutOfRangeRowsWithLineNumbers)
{
  const auto result = parse(
    "latitude,longitude\n"
    "22.6,120.2\n"      // line 2: ok
    "abc,120.2\n"       // line 3: not a number
    "91.0,120.2\n"      // line 4: out of range
    "22.6\n"            // line 5: too few columns
    "22.6,180.5\n"      // line 6: out of range
    "22.6,120.2,x\n"    // line 7: bad altitude
    "nan,120.2\n"       // line 8: not finite
    "22.7,120.3,1,2\n"  // line 9: too many columns
    "-22.7,-120.3\n");  // line 10: ok
  ASSERT_EQ(result.points.size(), 2u);
  EXPECT_DOUBLE_EQ(result.points[1].latitude, -22.7);
  ASSERT_EQ(result.warnings.size(), 7u);
  EXPECT_EQ(result.warnings[0], "line 3: not a number");
  EXPECT_EQ(result.warnings[1], "line 4: coordinate out of range");
  EXPECT_EQ(result.warnings[2], "line 5: expected 2 or 3 columns, got 1");
}

TEST(CsvPathLoader, ThrowsWhenNoValidPoints)
{
  EXPECT_THROW(parse("latitude,longitude,altitude\n"), std::runtime_error);
  EXPECT_THROW(parse(""), std::runtime_error);
  EXPECT_THROW(parse("lat,lon\n999,999\n"), std::runtime_error);
}

TEST(CsvPathLoader, ThrowsWhenFileIsMissing)
{
  EXPECT_THROW(load_path_csv("/nonexistent/path_data.csv"), std::runtime_error);
}
