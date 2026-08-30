class ApiException implements Exception {
  final String message;
  final int? statusCode;
  final Object? cause;

  const ApiException(
    this.message, {
    this.statusCode,
    this.cause,
  });

  bool get isUnauthorized => statusCode == 401;
  bool get isForbidden => statusCode == 403;
  bool get isNotFound => statusCode == 404;
  bool get isValidationError => statusCode == 400 || statusCode == 422;
  bool get isServerError => statusCode != null && statusCode! >= 500;

  @override
  String toString() {
    if (statusCode == null) {
      return message;
    }

    return '$message (HTTP $statusCode)';
  }
}

class NetworkException extends ApiException {
  const NetworkException(
    String message, {
    Object? cause,
  }) : super(message, cause: cause);
}

class TimeoutException extends NetworkException {
  const TimeoutException({
    Object? cause,
  }) : super(
          'The request timed out. Please check your connection and try again.',
          cause: cause,
        );
}
