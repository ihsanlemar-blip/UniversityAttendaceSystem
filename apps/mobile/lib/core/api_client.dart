import 'dart:convert';
import 'dart:io';

/// Basic API client providing backend connectivity and health probe inspection
/// for the Digital Student Attendance System mobile client.
class ApiClient {
  final String baseUrl;
  final HttpClient _client;

  ApiClient({
    String? baseUrl,
    HttpClient? client,
  })  : baseUrl = baseUrl ?? 'http://10.0.2.2:8000',
        _client = client ?? HttpClient();

  /// Check backend liveness (/health/live)
  Future<Map<String, dynamic>> checkLiveness() async {
    return _get('/health/live');
  }

  /// Check backend readiness (/health/ready)
  Future<Map<String, dynamic>> checkReadiness() async {
    return _get('/health/ready');
  }

  /// Fetch API v1 service metadata (/api/v1/)
  Future<Map<String, dynamic>> fetchApiMetadata() async {
    return _get('/api/v1/');
  }

  Future<Map<String, dynamic>> _get(String path) async {
    final uri = Uri.parse('$baseUrl$path');
    final request = await _client.getUrl(uri);
    request.headers.set(HttpHeaders.acceptHeader, 'application/json');
    final response = await request.close();

    final responseBody = await response.transform(utf8.decoder).join();
    if (responseBody.isEmpty) {
      return {'status_code': response.statusCode};
    }

    try {
      final decoded = jsonDecode(responseBody) as Map<String, dynamic>;
      return decoded;
    } catch (_) {
      return {
        'status_code': response.statusCode,
        'raw_body': responseBody,
      };
    }
  }

  void close() {
    _client.close(force: true);
  }
}
