#include "gnss_publisher/csv_path_loader.hpp"

#include <charconv>
#include <cmath>
#include <fstream>
#include <optional>
#include <stdexcept>
#include <string_view>

namespace gnss_publisher
{
namespace
{

std::string_view trim(std::string_view s)
{
  const auto is_space = [](char c) {return c == ' ' || c == '\t' || c == '\r' || c == '\n';};
  while (!s.empty() && is_space(s.front())) {
    s.remove_prefix(1);
  }
  while (!s.empty() && is_space(s.back())) {
    s.remove_suffix(1);
  }
  return s;
}

std::vector<std::string_view> split(std::string_view line, char delim)
{
  std::vector<std::string_view> fields;
  std::size_t start = 0;
  while (true) {
    const auto pos = line.find(delim, start);
    fields.push_back(trim(line.substr(start, pos - start)));
    if (pos == std::string_view::npos) {
      return fields;
    }
    start = pos + 1;
  }
}

// from_chars 不受 locale 影響、不丟例外；整個欄位都必須是有限的數字
std::optional<double> parse_double(std::string_view s)
{
  double value{};
  const char * last = s.data() + s.size();
  const auto [ptr, ec] = std::from_chars(s.data(), last, value);
  if (s.empty() || ec != std::errc{} || ptr != last || !std::isfinite(value)) {
    return std::nullopt;
  }
  return value;
}

}  // namespace

PathLoadResult parse_path_csv(std::istream & in)
{
  PathLoadResult result;
  std::string raw;
  std::size_t line_no = 0;
  bool seen_content = false;

  while (std::getline(in, raw)) {
    ++line_no;
    const auto line = trim(raw);
    if (line.empty() || line.front() == '#') {
      continue;
    }

    const auto fields = split(line, ',');
    const auto lat = parse_double(fields[0]);
    const bool is_header = !seen_content && !lat;
    seen_content = true;
    if (is_header) {
      continue;
    }

    const auto skip = [&](const std::string & reason) {
        result.warnings.push_back("line " + std::to_string(line_no) + ": " + reason);
      };

    if (fields.size() < 2 || fields.size() > 3) {
      skip("expected 2 or 3 columns, got " + std::to_string(fields.size()));
      continue;
    }
    const auto lon = parse_double(fields[1]);
    const auto alt = fields.size() == 3 ? parse_double(fields[2]) : std::optional<double>{0.0};
    if (!lat || !lon || !alt) {
      skip("not a number");
      continue;
    }
    if (std::abs(*lat) > 90.0 || std::abs(*lon) > 180.0) {
      skip("coordinate out of range");
      continue;
    }
    result.points.push_back({*lat, *lon, *alt});
  }

  if (result.points.empty()) {
    throw std::runtime_error("no valid GPS points in path CSV");
  }
  return result;
}

PathLoadResult load_path_csv(const std::string & path)
{
  std::ifstream file(path);
  if (!file) {
    throw std::runtime_error("cannot open path CSV: " + path);
  }
  return parse_path_csv(file);
}

}  // namespace gnss_publisher
