import User from '.'

test("check", () => {
  const user = new User()
  expect(user.say()).toEqual('My name is inoue')
});
