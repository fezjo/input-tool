import java.util.Scanner;

class sol_java {
    public static void main(String[] args) {
        Scanner scanner = new Scanner(System.in);
        if (scanner.hasNextInt()) {
            int x = scanner.nextInt();
            System.out.println(x);
        }
        scanner.close();
    }
}
