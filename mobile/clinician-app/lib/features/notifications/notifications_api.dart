import '../../core/api/clinician_api_client.dart';

class ClinicianNotificationsApi {
  ClinicianNotificationsApi(this.client);
  final ClinicianApiClient client;
  Future<Map<String, dynamic>> list() => client.get('/api/v1/notifications');
  Future<void> markRead(String id) => client.patch('/api/v1/notifications/$id/read');
  Future<Map<String, dynamic>> preferences() => client.get('/api/v1/notification-preferences');
  Future<Map<String, dynamic>> updatePreferences(Map<String, dynamic> value) =>
      client.patch('/api/v1/notification-preferences', body: value);
}
