#!/bin/bash
# Java Checkstyle linting

set -e

# Function to check if Checkstyle is available
check_checkstyle() {
    if command -v checkstyle >/dev/null 2>&1; then
        return 0
    fi
    
    # Check if Maven is available and has checkstyle plugin
    if command -v mvn >/dev/null 2>&1; then
        if [ -f pom.xml ]; then
            if grep -q "maven-checkstyle-plugin" pom.xml; then
                return 0
            fi
        fi
    fi
    
    # Check if Gradle is available and has checkstyle plugin
    if command -v gradle >/dev/null 2>&1; then
        if [ -f build.gradle ] || [ -f build.gradle.kts ]; then
            if grep -q "checkstyle" build.gradle* 2>/dev/null; then
                return 0
            fi
        fi
    fi
    
    echo "❌ Checkstyle not found. Please install it:"
    echo "  # For Maven, add to pom.xml:"
    echo "  <plugin>"
    echo "    <groupId>org.apache.maven.plugins</groupId>"
    echo "    <artifactId>maven-checkstyle-plugin</artifactId>"
    echo "  </plugin>"
    echo ""
    echo "  # For Gradle, add to build.gradle:"
    echo "  plugins { id 'checkstyle' }"
    echo ""
    echo "  # Or install standalone:"
    echo "  brew install checkstyle  # macOS"
    echo "  apt-get install checkstyle  # Ubuntu"
    return 1
}

# Check if Checkstyle is available
if ! check_checkstyle; then
    exit 1
fi

# Create basic checkstyle config if none exists
create_checkstyle_config() {
    if [ ! -f checkstyle.xml ] && [ ! -f config/checkstyle/checkstyle.xml ]; then
        echo "⚠️  No Checkstyle configuration found. Creating basic checkstyle.xml..."
        mkdir -p config/checkstyle
        cat > config/checkstyle/checkstyle.xml << 'EOF'
<?xml version="1.0"?>
<!DOCTYPE module PUBLIC
    "-//Checkstyle//DTD Checkstyle Configuration 1.3//EN"
    "https://checkstyle.org/dtds/configuration_1_3.dtd">

<module name="Checker">
    <property name="charset" value="UTF-8"/>
    <property name="severity" value="warning"/>
    <property name="fileExtensions" value="java, properties, xml"/>

    <!-- Checks for whitespace -->
    <module name="FileTabCharacter">
        <property name="eachLine" value="true"/>
    </module>

    <module name="TreeWalker">
        <!-- Checks for Naming Conventions -->
        <module name="ConstantName"/>
        <module name="LocalFinalVariableName"/>
        <module name="LocalVariableName"/>
        <module name="MemberName"/>
        <module name="MethodName"/>
        <module name="PackageName"/>
        <module name="ParameterName"/>
        <module name="StaticVariableName"/>
        <module name="TypeName"/>

        <!-- Checks for imports -->
        <module name="AvoidStarImport"/>
        <module name="IllegalImport"/>
        <module name="RedundantImport"/>
        <module name="UnusedImports">
            <property name="processJavadoc" value="false"/>
        </module>

        <!-- Checks for Size Violations -->
        <module name="MethodLength"/>
        <module name="ParameterNumber"/>

        <!-- Checks for whitespace -->
        <module name="EmptyForIteratorPad"/>
        <module name="GenericWhitespace"/>
        <module name="MethodParamPad"/>
        <module name="NoWhitespaceAfter"/>
        <module name="NoWhitespaceBefore"/>
        <module name="OperatorWrap"/>
        <module name="ParenPad"/>
        <module name="TypecastParenPad"/>
        <module name="WhitespaceAfter"/>
        <module name="WhitespaceAround"/>

        <!-- Modifier Checks -->
        <module name="ModifierOrder"/>
        <module name="RedundantModifier"/>

        <!-- Checks for blocks -->
        <module name="AvoidNestedBlocks"/>
        <module name="EmptyBlock"/>
        <module name="LeftCurly"/>
        <module name="NeedBraces"/>
        <module name="RightCurly"/>

        <!-- Checks for common coding problems -->
        <module name="EmptyStatement"/>
        <module name="EqualsHashCode"/>
        <module name="HiddenField"/>
        <module name="IllegalInstantiation"/>
        <module name="InnerAssignment"/>
        <module name="MissingSwitchDefault"/>
        <module name="SimplifyBooleanExpression"/>
        <module name="SimplifyBooleanReturn"/>

        <!-- Checks for class design -->
        <module name="DesignForExtension"/>
        <module name="FinalClass"/>
        <module name="HideUtilityClassConstructor"/>
        <module name="InterfaceIsType"/>
        <module name="VisibilityModifier"/>

        <!-- Security-related checks -->
        <module name="IllegalCatch"/>
        <module name="IllegalThrows"/>
    </module>
</module>
EOF
    fi
}

# Create basic config if none exists
create_checkstyle_config

# Run Checkstyle
echo "☕ Running Java Checkstyle..."

# Determine which method to use
if command -v checkstyle >/dev/null 2>&1; then
    # Use standalone checkstyle
    CONFIG_FILE=""
    if [ -f checkstyle.xml ]; then
        CONFIG_FILE="checkstyle.xml"
    elif [ -f config/checkstyle/checkstyle.xml ]; then
        CONFIG_FILE="config/checkstyle/checkstyle.xml"
    fi
    
    if [ -n "$CONFIG_FILE" ]; then
        checkstyle -c "$CONFIG_FILE" "$@"
    else
        checkstyle "$@"
    fi

elif command -v mvn >/dev/null 2>&1 && [ -f pom.xml ]; then
    # Use Maven plugin
    mvn checkstyle:check

elif command -v gradle >/dev/null 2>&1 && ([ -f build.gradle ] || [ -f build.gradle.kts ]); then
    # Use Gradle plugin
    gradle checkstyleMain

else
    echo "❌ Unable to run Checkstyle"
    exit 1
fi

echo "✅ Java Checkstyle check completed"
