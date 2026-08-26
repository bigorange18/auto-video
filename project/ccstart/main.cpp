#include <iostream>
#include <string>
#include <vector>
#include <unordered_map>

int main() {
    std::unordered_map<int, int> myMap;

    int target = 9;
    std::vector<int> nums = {2, 2, 7, 11, 15};

    int j = nums.size() - 1;
    for (int i = 0; i < j; i++) {
        int need = target - nums[i];
        if (myMap.count(need)) {
            myMap[nums[i]] = i;
            std::cout << "Index of " << need << " is: " << myMap[need] << std::endl;
            std::cout << "Index of " << nums[i] << " is: " << i << std::endl;
            return 0;
        } else {
            myMap[nums[i]] = i;
        }
    }
    return 0;
}