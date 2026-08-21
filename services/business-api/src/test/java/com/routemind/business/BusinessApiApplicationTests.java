package com.routemind.business;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class BusinessApiApplicationTests {

	@Autowired
	private MockMvc mockMvc;

	@Autowired
	private JdbcTemplate jdbcTemplate;

	@Test
	void actuatorHealthIsAvailable() throws Exception {
		mockMvc.perform(get("/actuator/health"))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.status").value("UP"));
	}

	@Test
	void systemInfoExposesRuntimeBoundary() throws Exception {
		mockMvc.perform(get("/api/v1/system"))
				.andExpect(status().isOk())
				.andExpect(jsonPath("$.service").value("business-api"))
				.andExpect(jsonPath("$.runtime").value("java"))
				.andExpect(jsonPath("$.architectureVersion").value("v1"));
	}

	@Test
	void flywayOwnsTheApplicationSchema() {
		Integer migrationCount = jdbcTemplate.queryForObject(
				"select count(*) from routemind.flyway_schema_history where version in ('1', '2') and success = true",
				Integer.class);

		assertThat(migrationCount).isEqualTo(2);
	}
}
