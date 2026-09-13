import 'package:flutter_test/flutter_test.dart';
import 'package:university_attendance_mobile/core/api_client.dart';

void main() {
  group('ApiClient', () {
    test('instantiates with default base URL', () {
      final client = ApiClient();
      expect(client.baseUrl, 'http://10.0.2.2:8000');
      client.close();
    });

    test('instantiates with custom base URL', () {
      final client = ApiClient(baseUrl: 'http://localhost:8000');
      expect(client.baseUrl, 'http://localhost:8000');
      client.close();
    });
  });
}
