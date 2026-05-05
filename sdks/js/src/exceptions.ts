export class VeklomError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'VeklomError';
  }
}

export class AuthError extends VeklomError {
  constructor(message: string) {
    super(message);
    this.name = 'AuthError';
  }
}

export class RateLimitError extends VeklomError {
  constructor(message: string) {
    super(message);
    this.name = 'RateLimitError';
  }
}

export class BudgetExceededError extends VeklomError {
  constructor(message: string) {
    super(message);
    this.name = 'BudgetExceededError';
  }
}
