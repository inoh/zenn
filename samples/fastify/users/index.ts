export type UserType = {
  id: string;
  name: string;
  email: string;
}

let users: Record<string, UserType> = {}

export class UserService {
  create(name: string, email: string): UserType | null {
    if (this.findByName(name)) {
      return null
    }
    const user = { id: crypto.randomUUID(), name, email }
    users[user.id] = user
    return user
  }

  find(id: string): UserType | undefined {
    return users[id]
  }

  findByName(name: string): UserType | undefined {
    return Object.values(users).find(user => user.name === name)
  }
}

export default {
  UserService
}
