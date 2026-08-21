package com.routemind.business;

import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.noClasses;

import com.tngtech.archunit.core.domain.JavaClasses;
import com.tngtech.archunit.core.importer.ClassFileImporter;
import com.tngtech.archunit.core.importer.ImportOption;
import org.junit.jupiter.api.Test;

class ArchitectureBoundaryTests {

	private static final String ROOT_PACKAGE = "com.routemind.business";
	private static final JavaClasses PRODUCTION_CLASSES = new ClassFileImporter()
			.withImportOption(ImportOption.Predefined.DO_NOT_INCLUDE_TESTS)
			.importPackages(ROOT_PACKAGE);

	@Test
	void domainDoesNotDependOnOuterLayers() {
		noClasses()
				.that().resideInAPackage("..domain..")
				.should().dependOnClassesThat().resideInAnyPackage("..application..", "..api..", "..infrastructure..")
				.check(PRODUCTION_CLASSES);
	}

	@Test
	void applicationDoesNotDependOnAdapters() {
		noClasses()
				.that().resideInAPackage("..application..")
				.should().dependOnClassesThat().resideInAnyPackage("..api..", "..infrastructure..")
				.check(PRODUCTION_CLASSES);
	}

	@Test
	void apiDoesNotDependOnInfrastructure() {
		noClasses()
				.that().resideInAPackage("..api..")
				.should().dependOnClassesThat().resideInAPackage("..infrastructure..")
				.check(PRODUCTION_CLASSES);
	}
}
