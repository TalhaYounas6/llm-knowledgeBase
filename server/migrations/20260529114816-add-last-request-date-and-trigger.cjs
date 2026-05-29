'use strict';

module.exports = {
   up: async (queryInterface, Sequelize) => {
    
    await queryInterface.addColumn('users', 'last_request_date', {
      type: Sequelize.DATEONLY,
      defaultValue: Sequelize.literal('CURRENT_DATE'),
      allowNull: false, 
    });

    //  Postgres Function
    await queryInterface.sequelize.query(`
      CREATE OR REPLACE FUNCTION check_and_reset_daily_limit()
      RETURNS TRIGGER AS $$
      BEGIN
          -- If the last request was before today, reset the counter to 0
          IF OLD.last_request_date < CURRENT_DATE THEN
              NEW.requests_this_day = 0;
              NEW.last_request_date = CURRENT_DATE;
          END IF;
          
          RETURN NEW;
      END;
      $$ LANGUAGE plpgsql;
    `);

    // Attach the Trigger to the users table
    await queryInterface.sequelize.query(`
      CREATE TRIGGER trigger_reset_daily_limit
      BEFORE UPDATE ON users
      FOR EACH ROW
      EXECUTE FUNCTION check_and_reset_daily_limit();
    `);
  },

   down: async (queryInterface, Sequelize) => {

    await queryInterface.sequelize.query(`
      DROP TRIGGER IF EXISTS trigger_reset_daily_limit ON users;
    `);

    await queryInterface.sequelize.query(`
      DROP FUNCTION IF EXISTS check_and_reset_daily_limit;
    `);

    await queryInterface.removeColumn('users', 'last_request_date');
  }
};