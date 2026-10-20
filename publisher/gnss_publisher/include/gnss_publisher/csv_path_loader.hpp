#ifndef GNSS_PUBLISHER__CSV_PATH_LOADER_HPP_
#define GNSS_PUBLISHER__CSV_PATH_LOADER_HPP_

#include <istream>
#include <string>
#include <vector>

namespace gnss_publisher
{

struct GeoPoint
{
  double latitude;
  double longitude;
  double altitude;
};

struct PathLoadResult
{
  std::vector<GeoPoint> points;
  // 被略過的行與原因（例如 "line 7: coordinate out of range"），由呼叫端記 log
  std::vector<std::string> warnings;
};

/// 解析 GPS 路徑 CSV，每行格式為 `latitude,longitude[,altitude]`（altitude 預設 0）。
/// - 略過空行、`#` 開頭的註解行，以及 CRLF 換行。
/// - 第一個有內容的行如果不是數字，視為表頭。
/// - 格式錯誤或超出範圍的行會略過，並記入 warnings。
/// 一個有效點都沒有時，丟出 std::runtime_error。
PathLoadResult parse_path_csv(std::istream & in);

/// 開檔後呼叫 parse_path_csv；檔案打不開時丟出 std::runtime_error。
PathLoadResult load_path_csv(const std::string & path);

}  // namespace gnss_publisher

#endif  // GNSS_PUBLISHER__CSV_PATH_LOADER_HPP_
