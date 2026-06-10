'use strict';

module.exports = {
  up: async (queryInterface, Sequelize) => {
    
    await queryInterface.sequelize.query(`
      DROP TRIGGER IF EXISTS trigger_reset_daily_limit ON users;
    `);

    await queryInterface.sequelize.query(`
      DROP FUNCTION IF EXISTS check_and_reset_daily_limit;
    `);

    // Recreate the function with the correct column name
    await queryInterface.sequelize.query(`
      CREATE OR REPLACE FUNCTION check_and_reset_daily_limit()
      RETURNS TRIGGER AS $$
      BEGIN
          -- If the last request was before today, reset the counter to 0
          IF OLD.last_request_date < CURRENT_DATE THEN
              NEW.requests_today = 0;
              NEW.last_request_date = CURRENT_DATE;
          END IF;
          
          RETURN NEW;
      END;
      $$ LANGUAGE plpgsql;
    `);

    // Reattach the trigger to the users table
    await queryInterface.sequelize.query(`
      CREATE TRIGGER trigger_reset_daily_limit
      BEFORE UPDATE ON users
      FOR EACH ROW
      EXECUTE FUNCTION check_and_reset_daily_limit();
    `);
  },

  down: async (queryInterface, Sequelize) => {
    
  }
};