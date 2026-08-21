package com.routemind.business;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication(proxyBeanMethods = false)
public class BusinessApiApplication {

	public static void main(String[] args) {
		SpringApplication.run(BusinessApiApplication.class, args);
	}

}
